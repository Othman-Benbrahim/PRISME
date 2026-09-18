"""Etape E3 : en-tete de provenance, identifiants, horloge d'enregistrement."""
import json
import unittest
from pathlib import Path

from commun import TMP, VAULT, reset_vault

from prisme_core import frontmatter, index, provenance
from prisme_core.app import create_app
from prisme_core.index import search as query
from prisme_core.routes import security


class TestFrontmatter(unittest.TestCase):
    def test_lecture(self):
        doc = "---\ntitle: Ma note\ntags:\n  - a\n  - b\naliases: [x, y]\nvide:\n---\n# Corps\n"
        self.assertEqual(frontmatter.parse(doc),
                         {"title": "Ma note", "tags": ["a", "b"], "aliases": ["x", "y"], "vide": []})
        self.assertEqual(frontmatter.strip(doc), "# Corps\n")

    def test_ecriture_preserve_le_reste(self):
        doc = "---\ntitle: Ma note\n# commentaire\naliases: [x]\n---\n# Corps\n\ntexte : deux points\n"
        out = frontmatter.update(doc, {"prisme_id": "abc123", "title": None})
        self.assertIn("# commentaire", out)
        self.assertIn("aliases: [x]", out)
        self.assertNotIn("title:", out)
        self.assertEqual(frontmatter.strip(out), "# Corps\n\ntexte : deux points\n")

    def test_creation_de_l_entete(self):
        out = frontmatter.update("# Sans en-tête\n\ncorps\n", {"prisme_id": "abc"})
        self.assertTrue(out.startswith("---\nprisme_id: abc\n---\n"))
        self.assertEqual(frontmatter.strip(out), "# Sans en-tête\n\ncorps\n")

    def test_valeurs_delicates(self):
        out = frontmatter.update("", {"a": "valeur: piégée", "b": "oui", "c": ["un", "deux"],
                                      "d": True, "e": "# pas un commentaire"})
        relu = frontmatter.parse(out)
        self.assertEqual(relu["a"], "valeur: piégée")
        self.assertEqual(relu["c"], ["un", "deux"])
        self.assertEqual(relu["e"], "# pas un commentaire")
        self.assertEqual(relu["d"], "true")

    def test_entete_non_fermee_intacte(self):
        doc = "---\ntitle: x\n# jamais refermé\n"
        self.assertEqual(frontmatter.parse(doc), {})
        self.assertEqual(frontmatter.strip(doc), doc)


class TestProvenance(unittest.TestCase):
    def setUp(self):
        reset_vault()

    def test_identifiant_pose_seulement_au_besoin(self):
        note = VAULT / "Alpha.md"
        avant = note.read_text(encoding="utf-8")
        self.assertEqual(provenance.lire(note).get("prisme_id"), None)
        ident = provenance.assurer_id(note)
        self.assertEqual(len(ident), 12)
        self.assertEqual(provenance.assurer_id(note), ident)          # idempotent
        apres = note.read_text(encoding="utf-8")
        self.assertEqual(frontmatter.strip(apres), avant)             # le corps n'a pas bougé
        self.assertTrue(list((VAULT / ".trash" / "versions").glob("*")), "instantané avant écriture")

    def test_estampille_complete(self):
        texte = provenance.estampiller("# Synthèse\n\ncorps\n", type="synthese", outil="rss",
                                       genere_par="modele (hote)", sources=["abc", "https://x.org/f"])
        meta = frontmatter.parse(texte)
        self.assertEqual(meta["prisme_type"], "synthese")
        self.assertEqual(meta["prisme_outil"], "rss")
        self.assertEqual(meta["prisme_sources"], ["abc", "https://x.org/f"])
        self.assertTrue(meta["prisme_enregistre_le"].startswith("20"))
        self.assertEqual(frontmatter.strip(texte), "# Synthèse\n\ncorps\n")
        # deuxième passage : on ne réestampille pas
        self.assertEqual(provenance.estampiller(texte, type="autre"), texte)

    def test_sources_vers_ids(self):
        ids = provenance.sources_vers_ids([str(VAULT / "Alpha.md"), "https://exemple.org/a", str(TMP / "absent.md")])
        self.assertEqual(len(ids[0]), 12)
        self.assertEqual(ids[1], "https://exemple.org/a")
        self.assertTrue(ids[2].endswith("absent.md"))                 # hors vault : conservé tel quel

    def test_champs_reserves_non_ecrits(self):
        meta = frontmatter.parse(provenance.estampiller("# X\n"))
        for champ in provenance.RESERVES:
            self.assertNotIn(champ, meta)


class TestRoutes(unittest.TestCase):
    def setUp(self):
        reset_vault()
        self.c = create_app(with_plugins=False).test_client()
        self.h = {"X-Prisme-Token": security.TOKEN}

    def post(self, url, data):
        return self.c.post(url, headers=self.h, json=data).get_json()

    def get(self, url, **q):
        return self.c.get(url, headers=self.h, query_string=q).get_json()

    def test_note_generee_estampillee_et_sources_identifiees(self):
        cible = VAULT / "Synthèse.md"
        r = self.post("/api/files/save", {
            "path": str(cible), "content": "# Synthèse\n\ncorps\n",
            "provenance": {"type": "synthese", "outil": "synthese-dossier",
                           "sources": [str(VAULT / "Alpha.md")], "preset": "Analyse"}})
        self.assertTrue(r["ok"])
        meta = frontmatter.parse(cible.read_text(encoding="utf-8"))
        self.assertEqual(meta["prisme_type"], "synthese")
        self.assertEqual(meta["prisme_preset"], "Analyse")
        self.assertIn("m", meta["prisme_genere_par"])                 # modèle de la configuration
        source_id = provenance.lire(VAULT / "Alpha.md")["prisme_id"]
        self.assertEqual(meta["prisme_sources"], [source_id])
        self.assertEqual(r["content"], cible.read_text(encoding="utf-8"))

        prov = self.get("/api/provenance", path=str(cible))
        self.assertTrue(prov["genere"])
        self.assertEqual(prov["meta"]["type"], "synthese")
        self.assertEqual([s["name"] for s in prov["sources"]], ["Alpha.md"])
        self.assertEqual(prov["sources"][0]["path"], str((VAULT / "Alpha.md").resolve()))

    def test_note_manuelle_intacte(self):
        contenu = "# Manuelle\n\nrien\n"
        self.post("/api/files/save", {"path": str(VAULT / "Manuelle.md"), "content": contenu})
        self.assertEqual((VAULT / "Manuelle.md").read_text(encoding="utf-8"), contenu)
        prov = self.get("/api/provenance", path=str(VAULT / "Manuelle.md"))
        self.assertFalse(prov["genere"])
        self.assertEqual(prov["sources"], [])

    def test_route_identifiant(self):
        r = self.post("/api/provenance/id", {"path": str(VAULT / "Alpha.md")})
        self.assertEqual(len(r["prisme_id"]), 12)
        self.assertEqual(self.post("/api/provenance/id", {"path": str(VAULT / "Alpha.md")})["prisme_id"],
                         r["prisme_id"])

    def test_hors_vault_refuse(self):
        for url, kwargs in (("/api/provenance", {"path": str(TMP / "x.md")}),):
            self.assertEqual(self.c.get(url, headers=self.h, query_string=kwargs).status_code, 403)
        self.assertEqual(self.c.post("/api/provenance/id", headers=self.h,
                                     json={"path": str(TMP / "x.md")}).status_code, 403)


class TestIndexProvenance(unittest.TestCase):
    def setUp(self):
        reset_vault()
        self.idx = index.get_index(VAULT)
        self.idx.refresh()

    def test_meta_indexee_et_recherche_par_identifiant(self):
        note = VAULT / "Gen.md"
        note.write_text(provenance.estampiller("# Gen\n\ncorps\n", type="synthese", outil="rss"),
                        encoding="utf-8")
        self.idx.touch(note)
        meta = query.note_meta(self.idx, str(note.resolve()))
        self.assertEqual((meta["type"], meta["outil"]), ("synthese", "rss"))
        trouve = query.by_prisme_id(self.idx, meta["prisme_id"])
        self.assertEqual(trouve["name"], "Gen.md")
        self.assertEqual([n["name"] for n in query.notes_generees(self.idx)], ["Gen.md"])

    def test_tags_du_frontmatter(self):
        note = VAULT / "Tagged.md"
        note.write_text("---\ntags: [veille, osint]\n---\n# T\n\ncorps #direct\n", encoding="utf-8")
        self.idx.touch(note)
        tags = {t["tag"] for t in query.tags(self.idx)}
        self.assertTrue({"veille", "osint", "direct"} <= tags)

    def test_entete_non_indexee_comme_texte(self):
        note = VAULT / "Secret.md"
        note.write_text("---\nprisme_id: zzz\nmotcle: confidentiel\n---\n# S\n\ncorps\n", encoding="utf-8")
        self.idx.touch(note)
        self.assertEqual(query.search(self.idx, "confidentiel"), [])
        self.assertEqual([r["name"] for r in query.search(self.idx, "corps")], ["Secret.md"])


if __name__ == "__main__":
    unittest.main()
