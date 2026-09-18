"""Etape E2 : index SQLite (segments, liens, tags, recherche plein texte)."""
import json
import shutil
import unicodedata
import time
import unittest
from pathlib import Path
from unittest import mock

from commun import ROOT, TMP, VAULT, reset_vault

from prisme_core import config, index
from prisme_core.app import create_app
from prisme_core.index import indexer, search as query, store
from prisme_core.index.resolver import LinkResolver
from prisme_core.index.segmenter import GROUP_TARGET, SECTION_MAX, segment
from prisme_core.routes import security

EVAL_VAULT = ROOT / "tests" / "fixtures" / "vault-eval"
EVAL_QUESTIONS = ROOT / "evaluation" / "questions-reference.jsonl"


class TestSegmenteur(unittest.TestCase):
    def test_un_segment_par_titre_jusqu_au_niveau_3(self):
        doc = ("Intro.\n\n# Un\ncorps un\n\n## Deux\ncorps deux\n\n"
               "#### Quatre\nreste dans deux\n\n### Trois\ncorps trois\n")
        segs = segment(doc)
        self.assertEqual([s.heading for s in segs],
                         ["", "Un", "Un > Deux", "Un > Deux > Trois"])
        self.assertIn("#### Quatre", segs[2].text)
        self.assertEqual(segs[1].start_line, 3)

    def test_frontmatter_hors_du_texte(self):
        segs = segment("---\ntags: [a]\nsecret: xyz\n---\n\n# T\ncorps\n")
        self.assertNotIn("secret", "".join(s.text for s in segs))

    def test_bloc_de_code_jamais_coupe(self):
        doc = "# T\n\n```python\n" + "ligne = 1\n\n" * 700 + "```\n"
        segs = segment(doc)
        self.assertEqual(len(segs), 1)
        self.assertGreater(len(segs[0].text), SECTION_MAX)

    def test_titre_setext(self):
        segs = segment("Titre\n=====\ncorps\n\nSous\n----\nautre\n")
        self.assertEqual([(s.heading, s.level) for s in segs], [("Titre", 1), ("Titre > Sous", 2)])

    def test_note_sans_titre_regroupee(self):
        doc = "\n\n".join("Paragraphe %d. %s" % (i, "mot " * 40) for i in range(12))
        segs = segment(doc)
        self.assertGreater(len(segs), 1)
        self.assertTrue(all(len(s.text) <= SECTION_MAX for s in segs))
        self.assertTrue(any(len(s.text) >= GROUP_TARGET / 2 for s in segs))

    def test_section_longue_coupee_entre_paragraphes(self):
        doc = "# T\n\n" + "\n\n".join("Para %d. %s" % (i, "mot " * 60) for i in range(20))
        segs = segment(doc)
        self.assertGreater(len(segs), 1)
        self.assertTrue(all(len(s.text) <= SECTION_MAX + 200 for s in segs))
        self.assertTrue(all(s.text.startswith("Para") for s in segs))


class TestResolveur(unittest.TestCase):
    def setUp(self):
        self.paths = ["/v/Note.md", "/v/sous/Note.md", "/v/sous/Autre.md", "/v/references/OSINT.md"]
        self.r = LinkResolver(self.paths)

    def test_cascade(self):
        self.assertEqual(self.r.resolve("Autre", "/v/sous/Note.md"), "/v/sous/Autre.md")   # relatif
        self.assertEqual(self.r.resolve("references/OSINT", "/v/Note.md"), "/v/references/OSINT.md")
        self.assertEqual(self.r.resolve("Note", "/v/x/Inconnu.md"), "/v/Note.md")          # plus court
        self.assertEqual(self.r.resolve("sous/Note.md", None), "/v/sous/Note.md")
        self.assertIsNone(self.r.resolve("Inexistant", "/v/Note.md"))
        self.assertIsNone(self.r.resolve("", None))

    def test_stable(self):
        self.assertEqual(LinkResolver(reversed(self.paths)).resolve("Note", None), "/v/Note.md")


class IndexEnv(unittest.TestCase):
    def setUp(self):
        reset_vault()
        self.idx = index.get_index(VAULT)
        self.idx.refresh()

    def rows(self, sql, *args):
        with self.idx.read() as conn:
            return [tuple(r) for r in conn.execute(sql, args)]


class TestIndexation(IndexEnv):
    def test_contenu_initial(self):
        self.assertEqual(self.rows("SELECT count(*) FROM files")[0][0], 2)
        self.assertEqual(self.rows("SELECT count(*) FROM segments")[0][0], 2)
        self.assertEqual(sorted(t[0] for t in self.rows("SELECT tag FROM tags")), ["t1"])
        self.assertEqual(self.rows("SELECT count(*) FROM links WHERE target_path IS NOT NULL")[0][0], 2)

    def test_incremental_par_segment(self):
        note = VAULT / "Alpha.md"
        note.write_text("# Alpha\n\n[[Beta]] #t1\n\nmot-unique\n\n## Nouvelle\n\najout\n", encoding="utf-8")
        avant = dict(self.rows("SELECT sha256, id FROM segments"))
        self.idx.touch(note)
        apres = dict(self.rows("SELECT sha256, id FROM segments"))
        communs = set(avant) & set(apres)
        self.assertTrue(communs, "le segment inchangé doit garder son identifiant")
        for sha in communs:
            self.assertEqual(avant[sha], apres[sha])
        self.assertEqual(len(apres), 3)

    def test_fichier_inchange_non_reindexe(self):
        (VAULT / "Alpha.md").touch()               # date modifiée, contenu identique
        ids = self.rows("SELECT id FROM segments ORDER BY id")
        self.idx._last_check = 0
        self.idx.refresh()
        self.assertEqual(self.rows("SELECT id FROM segments ORDER BY id"), ids)

    def test_suppression_et_liens_orphelins(self):
        (VAULT / "sous" / "Beta.md").unlink()
        self.idx.touch(VAULT / "sous" / "Beta.md")
        self.assertEqual(self.rows("SELECT count(*) FROM files")[0][0], 1)
        self.assertEqual(self.rows("SELECT count(*) FROM links WHERE target_path IS NOT NULL")[0][0], 0)

    def test_nouveau_fichier_resout_les_liens_existants(self):
        (VAULT / "Alpha.md").write_text("# Alpha\n\nvers [[Gamma]]\n", encoding="utf-8")
        self.idx.touch(VAULT / "Alpha.md")
        self.assertEqual(self.rows("SELECT raw FROM links WHERE target_path IS NULL"), [("Gamma",)])
        (VAULT / "Gamma.md").write_text("# Gamma\n", encoding="utf-8")
        self.idx.touch(VAULT / "Gamma.md")          # l'arrivee d'une note re-resout tous les liens
        self.assertEqual(self.rows("SELECT raw FROM links WHERE target_path IS NULL"), [])
        self.assertIn(("Gamma", str((VAULT / "Gamma.md").resolve())),
                      self.rows("SELECT raw, target_path FROM links"))

    def test_reconstruction_atomique(self):
        (VAULT / "Delta.md").write_text("# Delta\n\ncorps\n", encoding="utf-8")
        self.idx.rebuild()
        self.assertEqual(self.idx.state, "pret")
        self.assertEqual(self.rows("SELECT count(*) FROM files")[0][0], 3)
        self.assertFalse(Path(str(self.idx.db_path) + ".nouveau").exists())

    def test_base_dans_le_profil_et_reconstructible(self):
        self.assertTrue(str(self.idx.db_path).startswith(str(TMP / "profil")))
        self.assertIn(str(self.idx.root), json.loads(store.MAP_FILE.read_text(encoding="utf-8")).values())
        self.idx.db_path.unlink()
        index.forget_all()
        idx = index.get_index(VAULT)
        idx.refresh()
        self.assertEqual(idx.status()["files"], 2)

    def test_schema_incompatible_reconstruit(self):
        with store.session(self.idx.db_path) as conn:
            conn.execute("PRAGMA user_version = 999")
            conn.commit()
        index.forget_all()
        idx = index.get_index(VAULT)
        self.assertEqual(idx.status()["files"], 0)
        idx.refresh()
        self.assertEqual(idx.status()["files"], 2)

    def test_pas_de_plafond_de_5000(self):
        gros = TMP / "gros-vault"
        shutil.rmtree(gros, ignore_errors=True)
        (gros / "sous").mkdir(parents=True)
        for i in range(5200):
            (gros / ("sous" if i % 2 else "") / f"n{i}.md").write_text(f"# N{i}\n\ncorps {i}\n", encoding="utf-8")
        self.assertEqual(len(list(indexer.walk_notes(gros))), 5200)


class TestRecherche(IndexEnv):
    def test_extraits_et_surlignage(self):
        res = query.search(self.idx, "mot-unique")
        self.assertEqual([r["name"] for r in res], ["Alpha.md"])
        self.assertIn(query.MARK_OPEN, res[0]["matches"][0]["text"])

    def test_sans_fts5_repli_sur_like(self):
        with mock.patch.object(store, "_FTS_OK", False):
            res = query.search(self.idx, "mot-unique")
        self.assertEqual([r["name"] for r in res], ["Alpha.md"])

    def test_portee_limitee_a_un_sous_dossier(self):
        self.assertEqual([r["name"] for r in query.search(self.idx, "Beta", root_filter=str(VAULT / "sous"))],
                         ["Beta.md"])

    def test_graphe_et_backlinks(self):
        g = query.graph(self.idx)
        self.assertEqual(len(g["nodes"]), 2)
        self.assertEqual(len(g["links"]), 1)
        self.assertEqual(sorted(n["degree"] for n in g["nodes"]), [2, 2])
        bl = query.backlinks(self.idx, str((VAULT / "Alpha.md").resolve()))
        self.assertEqual([b["name"] for b in bl], ["Beta.md"])
        self.assertIn("Alpha", bl[0]["ctx"])


def _nfc(x):
    """Les noms de fichiers accentues n'ont pas la meme forme selon les systemes."""
    return unicodedata.normalize("NFC", str(x))


class TestQuestionsDeReference(unittest.TestCase):
    """Les questions de reference mesurent la qualite de la recherche (evaluation/)."""

    ATTENDUS = {"Superprévision.md", "Signaux faibles.md", "Écriture fractale.md",
                "Jardinage.md", "Journal 2026-03-12.md", "references/OSINT.md"}

    @classmethod
    def setUpClass(cls):
        cls.vault = TMP / "vault-eval"
        shutil.rmtree(cls.vault, ignore_errors=True)
        shutil.copytree(EVAL_VAULT, cls.vault)
        index.forget_all()
        cls.idx = index.get_index(cls.vault)
        cls.idx.refresh()

    def test_vault_de_reference_intact(self):
        """Garde-fou : une decompression qui abime les accents fausserait tout le reste."""
        presents = {_nfc(p.relative_to(self.vault).as_posix())
                    for p in self.vault.rglob("*.md")}
        self.assertEqual(presents, {_nfc(x) for x in self.ATTENDUS},
                         "Noms de fichiers du vault de référence inattendus. Cause probable : "
                         "l'archive a été décompressée par un outil qui abîme les accents "
                         "(Expand-Archive sur une archive sans drapeau UTF-8). "
                         "Supprimez tests/fixtures/vault-eval et reposez la livraison.")

    def test_toutes_les_questions_trouvent_la_note_attendue(self):
        echecs = []
        for line in EVAL_QUESTIONS.read_text(encoding="utf-8").splitlines():
            cas = json.loads(line)
            res = query.search(self.idx, cas["question"], limit_files=3)
            trouves = [_nfc(Path(r["path"]).relative_to(self.vault).as_posix()) for r in res]
            if _nfc(cas["attendu"]) not in trouves[:3]:
                echecs.append(f"{cas['id']} « {cas['question']} » → {trouves} (attendu {cas['attendu']})")
        self.assertEqual(echecs, [], "\n".join(echecs))

    def test_liens_du_vault_de_reference(self):
        with self.idx.read() as conn:
            total, resolus = conn.execute("SELECT count(*), count(target_path) FROM links").fetchone()
        self.assertEqual((total, resolus), (3, 3))


class TestRoutes(unittest.TestCase):
    def setUp(self):
        reset_vault()
        self.c = create_app(with_plugins=False).test_client()
        self.h = {"X-Prisme-Token": security.TOKEN}

    def get(self, url, **q):
        return self.c.get(url, headers=self.h, query_string=q).get_json()

    def test_recherche_tags_graphe_backlinks_par_l_index(self):
        self.assertEqual([r["name"] for r in self.get("/api/search", q="mot-unique")["results"]], ["Alpha.md"])
        self.assertIn("t1", [t["tag"] for t in self.get("/api/tags")["tags"]])
        self.assertEqual(len(self.get("/api/files/graph")["links"]), 1)
        bl = self.get("/api/files/backlinks", path=str(VAULT / "Alpha.md"))["backlinks"]
        self.assertEqual([b["name"] for b in bl], ["Beta.md"])
        found = self.get("/api/files/find", name="Beta")
        self.assertEqual(Path(found["path"]).name, "Beta.md")

    def test_ecriture_immediatement_visible(self):
        self.c.post("/api/files/save", headers=self.h,
                    json={"path": str(VAULT / "Alpha.md"), "content": "# Alpha\n\nmirabelle\n"})
        self.assertEqual([r["name"] for r in self.get("/api/search", q="mirabelle")["results"]], ["Alpha.md"])
        self.c.post("/api/files/delete", headers=self.h, json={"path": str(VAULT / "Alpha.md")})
        self.assertEqual(self.get("/api/search", q="mirabelle")["results"], [])

    def test_etat_et_reconstruction(self):
        st = self.get("/api/index/status")
        self.assertEqual(st["state"], "pret")
        self.assertEqual(st["fulltext"], "fts5")
        self.assertTrue(st["db"].endswith(".db"))
        r = self.c.post("/api/index/rebuild", headers=self.h, json={}).get_json()
        self.assertTrue(r["started"])
        index.get_index()._thread.join(timeout=30)
        st = self.get("/api/index/status")
        self.assertEqual((st["state"], st["files"]), ("pret", 2))

    def test_dir_hors_vault_toujours_refuse(self):
        r = self.c.get("/api/search", headers=self.h, query_string={"q": "x", "dir": str(TMP)})
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
