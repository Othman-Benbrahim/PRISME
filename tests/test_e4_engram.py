"""Etape E4 : ENGRAM — contrat d'extraction, identité des passages, ingestion idempotente."""
import json
import shutil
import unittest
from pathlib import Path

from commun import ROOT, TMP, VAULT, reset_vault

from prisme_core import engram, frontmatter, index
from prisme_core.app import create_app
from prisme_core.engram import contrat, identite, ingestion, notes
from prisme_core.engram.contrat import Passage, SourceInvalide
from prisme_core.index import search as query
from prisme_core.routes import security

EXPORTS = ROOT / "tests" / "fixtures" / "exports"


class TestExtracteurs(unittest.TestCase):
    def extraire(self, nom):
        return contrat.extraire(EXPORTS / nom)

    def test_chatgpt(self):
        ex, infos = self.extraire("chatgpt-conversations.json")
        self.assertEqual(infos["extracteur"], "chatgpt")
        self.assertEqual([p.titre for p in ex.passages],
                         ["Mesure des prévisions · Vous", "Mesure des prévisions · Assistant"])
        self.assertIn("score de Brier", ex.passages[1].texte)
        self.assertTrue(ex.passages[0].date.startswith("2026-03-04"))

    def test_claude(self):
        ex, infos = self.extraire("claude-conversations.json")
        self.assertEqual(infos["extracteur"], "claude")
        self.assertIn("signal faible", ex.passages[0].texte)
        self.assertEqual(ex.titre, "Signaux faibles", "un export d'une seule conversation en prend le titre")

    def test_mistral(self):
        ex, infos = self.extraire("mistral-lechat-export.json")
        self.assertEqual(infos["extracteur"], "mistral")
        self.assertEqual(len(ex.passages), 2)
        self.assertIn("OSINT", ex.passages[0].texte)

    def test_html_sans_script_ni_style(self):
        ex, infos = self.extraire("article.html")
        self.assertEqual(infos["extracteur"], "html")
        self.assertEqual(ex.titre, "Un article de veille")
        texte = "\n".join(p.texte for p in ex.passages)
        self.assertIn("Premier paragraphe", texte)
        self.assertNotIn("var x", texte)
        self.assertNotIn("color:red", texte)

    def test_markdown_par_segments(self):
        src = TMP / "note-source.md"
        src.write_text("# Titre\n\ncorps un\n\n## Section\n\ncorps deux\n", encoding="utf-8")
        ex, infos = contrat.extraire(src)
        self.assertEqual(infos["extracteur"], "texte")
        self.assertEqual([p.titre for p in ex.passages], ["Titre", "Titre > Section"])

    def test_json_inconnu_reste_lisible(self):
        src = TMP / "donnees.json"
        src.write_text(json.dumps({"a": [1, 2, 3], "b": "texte"}), encoding="utf-8")
        ex, infos = contrat.extraire(src)
        self.assertEqual(infos["extracteur"], "json")
        self.assertIn("texte", ex.passages[0].texte)

    def test_controles_prealables(self):
        vide = TMP / "vide.md"
        vide.write_text("", encoding="utf-8")
        for chemin in (TMP / "absent.md", vide):
            with self.assertRaises(SourceInvalide):
                contrat.extraire(chemin)
        inconnu = TMP / "image.png"
        inconnu.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 50)
        with self.assertRaises(SourceInvalide):
            contrat.extraire(inconnu)

    def test_empreinte_verifiee_apres_lecture(self):
        src = TMP / "mouvant.md"
        src.write_text("# A\n\ncorps\n", encoding="utf-8")
        vrai_lire = contrat.lire_texte

        def lire_et_modifier(chemin):
            texte = vrai_lire(chemin)
            chemin.write_text("# A\n\nautre corps\n", encoding="utf-8")   # le fichier change pendant la lecture
            return texte
        contrat.lire_texte = lire_et_modifier
        try:
            with self.assertRaises(SourceInvalide) as e:
                contrat.extraire(src)
            self.assertIn("pendant la lecture", str(e.exception))
        finally:
            contrat.lire_texte = vrai_lire


class TestIdentite(unittest.TestCase):
    def anciens(self, textes):
        return [{"id": f"p-{i:08d}", "empreinte": Passage(texte=t).empreinte, "texte": t, "position": i}
                for i, t in enumerate(textes)]

    def test_inchange_deplace_modifie_nouveau_retire(self):
        anciens = self.anciens(["alpha texte", "beta texte", "gamma texte", "delta texte"])
        nouveaux = [Passage(texte="alpha texte"),                       # inchangé
                    Passage(texte="gamma texte"),                       # déplacé
                    Passage(texte="beta texte revu et légèrement corrigé ici"),  # trop modifié
                    Passage(texte="tout nouveau")]                      # nouveau
        att, ret = identite.reconcilier(anciens, nouveaux)
        self.assertEqual(att[0]["statut"], "inchange")
        self.assertEqual((att[1]["statut"], att[1]["id"]), ("deplace", "p-00000002"))
        self.assertEqual(att[3]["statut"], "nouveau")
        self.assertIn("p-00000003", [r["id"] for r in ret])             # delta retiré

    def test_retouche_legere_garde_l_identifiant(self):
        anciens = self.anciens(["Le score de Brier mesure la calibration des prévisions."])
        nouveaux = [Passage(texte="Le score de Brier mesure la calibration des prévisions annoncées.")]
        att, ret = identite.reconcilier(anciens, nouveaux)
        self.assertEqual((att[0]["id"], att[0]["statut"]), ("p-00000000", "modifie"))
        self.assertEqual(ret, [])

    def test_ambiguite_donne_un_nouvel_identifiant(self):
        anciens = self.anciens(["texte presque pareil A", "texte presque pareil B"])
        nouveaux = [Passage(texte="texte presque pareil C")]
        att, _ = identite.reconcilier(anciens, nouveaux)
        self.assertEqual(att[0]["statut"], "nouveau", "dans le doute, pas de rattachement")


class EngramBase(unittest.TestCase):
    def setUp(self):
        reset_vault()
        ingestion.ecrire_registre({})
        self.src = TMP / "import" / "conversations.json"
        self.src.parent.mkdir(exist_ok=True)
        shutil.copy(EXPORTS / "claude-conversations.json", self.src)

    def notes_de(self, res):
        return [Path(f) for f in res["notes"]]


class TestIngestion(EngramBase):
    def test_import_puis_reimport_identique(self):
        res = engram.importer(self.src)
        self.assertEqual(res["etat"], "nouvelle")
        self.assertEqual(res["comptes"], {"nouveau": 2, "inchange": 0, "deplace": 0, "modifie": 0, "retire": 0})
        note = self.notes_de(res)[0]
        contenu = note.read_text(encoding="utf-8")
        meta = frontmatter.parse(contenu)
        self.assertEqual(meta["prisme_type"], "import")
        self.assertEqual(meta["prisme_outil"], "engram")
        self.assertEqual(meta["prisme_source_mode"], "reference")
        self.assertEqual(meta["prisme_source_sha256"], contrat.sha256_fichier(self.src))
        self.assertIn("claude v1", meta["prisme_source_extracteur"])
        self.assertIn("signal faible", contenu)
        self.assertEqual(len(notes.passages_existants(contenu)), 2)

        encore = engram.importer(self.src)                     # idempotence
        self.assertEqual(encore["etat"], "inchangee")
        self.assertEqual(note.read_text(encoding="utf-8"), contenu)

    def test_source_modifiee_garde_les_identifiants(self):
        res = engram.importer(self.src)
        note = self.notes_de(res)[0]
        avant = {p["id"] for p in notes.passages_existants(note.read_text(encoding="utf-8"))}

        data = json.loads(self.src.read_text(encoding="utf-8"))
        data[0]["chat_messages"][1]["content"][0]["text"] += " Sa détection suppose une veille."
        data[0]["chat_messages"].append({"sender": "human", "created_at": "2026-02-11T10:00:00+00:00",
                                         "content": [{"type": "text", "text": "Et un exemple concret ?"}]})
        self.src.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        res2 = engram.importer(self.src)
        self.assertEqual(res2["etat"], "modifiee")
        self.assertEqual(res2["comptes"]["inchange"], 1)
        self.assertEqual(res2["comptes"]["modifie"], 1)
        self.assertEqual(res2["comptes"]["nouveau"], 1)
        apres = notes.passages_existants(Path(res2["notes"][0]).read_text(encoding="utf-8"))
        self.assertTrue(avant <= {p["id"] for p in apres}, "les identifiants existants sont conservés")

    def test_passage_disparu_archive_en_rouge(self):
        res = engram.importer(self.src)
        note = self.notes_de(res)[0]
        data = json.loads(self.src.read_text(encoding="utf-8"))
        disparu = data[0]["chat_messages"].pop(1)["content"][0]["text"]
        self.src.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        res2 = engram.importer(self.src)
        self.assertEqual(res2["comptes"]["retire"], 1)
        contenu = note.read_text(encoding="utf-8")
        self.assertIn("> [!danger] Retiré de la source", contenu)
        self.assertIn(disparu[:40], contenu)
        self.assertEqual(len(notes.passages_existants(contenu)), 1)
        self.assertEqual(len(notes.archives_existantes(contenu)), 1)

        # le passage revient : il quitte l'archive
        data[0]["chat_messages"].insert(1, {"sender": "assistant", "created_at": "2026-02-11T09:30:40+00:00",
                                            "content": [{"type": "text", "text": disparu}]})
        self.src.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        engram.importer(self.src)
        contenu = note.read_text(encoding="utf-8")
        self.assertEqual(len(notes.passages_existants(contenu)), 2)

    def test_mode_copie(self):
        res = engram.importer(self.src, mode="copie")
        meta = frontmatter.parse(self.notes_de(res)[0].read_text(encoding="utf-8"))
        self.assertEqual(meta["prisme_source_mode"], "copie")
        copies = list((VAULT / "_sources").glob("*conversations.json"))
        self.assertEqual(len(copies), 1)
        self.assertEqual(contrat.sha256_fichier(copies[0]), contrat.sha256_fichier(self.src))

    def test_decoupage_en_parties_et_sommaire(self):
        gros = TMP / "import" / "gros.md"
        gros.write_text("\n\n".join(f"## Section {i}\n\n" + ("phrase longue " * 200) for i in range(12)),
                        encoding="utf-8")
        res = engram.importer(gros, seuil=8000)
        self.assertGreater(res["parties"], 1)
        fichiers = self.notes_de(res)
        sommaire = fichiers[0].read_text(encoding="utf-8")
        self.assertIn("répartie en plusieurs parties", sommaire)
        for f in fichiers[1:]:
            self.assertIn("prisme_source_partie", frontmatter.parse(f.read_text(encoding="utf-8")))

    def test_controle_des_sources(self):
        engram.importer(self.src)
        self.assertEqual([s["etat"] for s in engram.controler()], ["intacte"])
        self.src.write_text(self.src.read_text(encoding="utf-8") + " ", encoding="utf-8")
        self.assertEqual([s["etat"] for s in engram.controler()], ["modifiée"])
        self.src.unlink()
        self.assertEqual([s["etat"] for s in engram.controler()], ["disparue"])

    def test_notes_indexees_et_recherchables(self):
        res = engram.importer(self.src)
        idx = index.get_index(VAULT)
        idx.refresh()
        trouve = query.search(idx, "signal faible")
        self.assertIn(Path(res["notes"][0]).name, [r["name"] for r in trouve])
        meta = query.note_meta(idx, str(Path(res["notes"][0]).resolve()))
        self.assertEqual(meta["outil"], "engram")


class TestRoutes(EngramBase):
    def setUp(self):
        super().setUp()
        self.c = create_app(with_plugins=False).test_client()
        self.h = {"X-Prisme-Token": security.TOKEN}

    def post(self, url, data):
        return self.c.post(url, headers=self.h, json=data)

    def test_parcours_complet(self):
        insp = self.post("/api/engram/inspect", {"chemin": str(self.src)}).get_json()
        self.assertEqual((insp["etat"], insp["extracteur"]), ("nouvelle", "claude v1"))
        res = self.post("/api/engram/import", {"chemin": str(self.src), "mode": "reference"}).get_json()
        self.assertEqual(res["etat"], "nouvelle")
        sources = self.c.get("/api/engram/sources", headers=self.h).get_json()["sources"]
        self.assertEqual(sources[0]["etat"], "intacte")
        self.assertEqual(self.post("/api/engram/oublier", {"cle": sources[0]["cle"]}).status_code, 200)
        self.assertEqual(self.c.get("/api/engram/sources", headers=self.h).get_json()["sources"], [])

    def test_erreurs(self):
        self.assertEqual(self.post("/api/engram/inspect", {"chemin": str(TMP / "absent.json")}).status_code, 400)
        self.assertEqual(self.post("/api/engram/import", {"chemin": str(self.src), "mode": "ailleurs"}).status_code, 400)
        self.assertEqual(self.post("/api/engram/import", {"chemin": str(self.src),
                                                          "dossier": str(TMP)}).status_code, 403)

    def test_formats(self):
        d = self.c.get("/api/engram/formats", headers=self.h).get_json()
        self.assertIn(".json", d["formats"])
        self.assertIn(".html", d["formats"])


if __name__ == "__main__":
    unittest.main()
