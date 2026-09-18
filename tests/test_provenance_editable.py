"""Fiche de provenance modifiable : ecrire, corriger et retirer des champs a la main."""
import unittest

from commun import TMP, VAULT, reset_vault

from prisme_core import frontmatter, index, provenance
from prisme_core.app import create_app
from prisme_core.index import search as query
from prisme_core.routes import security


class TestValidation(unittest.TestCase):
    def test_champs_acceptes(self):
        propres = provenance.valider({"prisme_type": "source", "prisme_publie_le": "2026-03-01",
                                      "prisme_outil": "", "prisme_valide_du": "2026-01-02"})
        self.assertEqual(propres["prisme_type"], "source")
        self.assertIsNone(propres["prisme_outil"])                  # vide = retirer la cle
        self.assertEqual(propres["prisme_valide_du_etat"], "date")  # etat deduit d'une date saisie

    def test_champs_refuses(self):
        for champs in ({"prisme_id": "abc"}, {"prisme_sources": ["x"]}, {"inconnu": "x"},
                       {"prisme_publie_le": "hier"}, {"prisme_valide_au_etat": "peut-etre"},
                       {"prisme_valide_du_etat": "date"}, {"prisme_type": "x" * 600}):
            with self.subTest(champs=champs):
                with self.assertRaises(provenance.ChampInvalide):
                    provenance.valider(champs)

    def test_date_inconnue_et_ouverte(self):
        self.assertEqual(provenance.valider({"prisme_valide_au_etat": "ouverte"}),
                         {"prisme_valide_au_etat": "ouverte"})


class TestRoute(unittest.TestCase):
    def setUp(self):
        reset_vault()
        self.c = create_app(with_plugins=False).test_client()
        self.h = {"X-Prisme-Token": security.TOKEN}
        self.note = VAULT / "Alpha.md"

    def post(self, url, data):
        return self.c.post(url, headers=self.h, json=data)

    def meta(self):
        return frontmatter.parse(self.note.read_text(encoding="utf-8"))

    def test_ajout_sur_note_sans_provenance(self):
        corps = self.note.read_text(encoding="utf-8")
        r = self.post("/api/provenance", {
            "path": str(self.note),
            "champs": {"prisme_type": "source", "prisme_outil": "saisie manuelle",
                       "prisme_publie_le": "2026-02-10"},
            "sources": ["https://exemple.org/article", str(VAULT / "sous" / "Beta.md")]}).get_json()
        self.assertTrue(r["ok"])
        meta = self.meta()
        self.assertEqual(meta["prisme_type"], "source")
        self.assertEqual(meta["prisme_publie_le"], "2026-02-10")
        self.assertEqual(len(meta["prisme_id"]), 12)                 # identifiant pose au passage
        beta_id = provenance.lire(VAULT / "sous" / "Beta.md")["prisme_id"]
        self.assertEqual(meta["prisme_sources"], ["https://exemple.org/article", beta_id])
        self.assertEqual(frontmatter.strip(self.note.read_text(encoding="utf-8")), corps)
        self.assertEqual(r["content"], self.note.read_text(encoding="utf-8"))
        self.assertTrue(list((VAULT / ".trash" / "versions").glob("*")))

    def test_correction_et_retrait(self):
        self.post("/api/provenance", {"path": str(self.note),
                                      "champs": {"prisme_type": "source", "prisme_preset": "Veille"}})
        ident = self.meta()["prisme_id"]
        self.post("/api/provenance", {"path": str(self.note),
                                      "champs": {"prisme_type": "note", "prisme_preset": ""}})
        meta = self.meta()
        self.assertEqual(meta["prisme_type"], "note")
        self.assertNotIn("prisme_preset", meta)
        self.assertEqual(meta["prisme_id"], ident)                   # l'identifiant ne change pas

    def test_sources_remplacees_puis_videes(self):
        self.post("/api/provenance", {"path": str(self.note), "champs": {},
                                      "sources": ["https://a.org", "https://b.org"]})
        self.assertEqual(self.meta()["prisme_sources"], ["https://a.org", "https://b.org"])
        self.post("/api/provenance", {"path": str(self.note), "champs": {}, "sources": []})
        self.assertNotIn("prisme_sources", self.meta())

    def test_index_mis_a_jour(self):
        self.post("/api/provenance", {"path": str(self.note),
                                      "champs": {"prisme_type": "source", "prisme_outil": "import"}})
        idx = index.get_index(VAULT)
        meta = query.note_meta(idx, str(self.note.resolve()))
        self.assertEqual((meta["type"], meta["outil"]), ("source", "import"))
        prov = self.c.get("/api/provenance", headers=self.h,
                          query_string={"path": str(self.note)}).get_json()
        self.assertFalse(prov["genere"], "un outil sans modèle n'est pas une note générée")
        self.assertEqual(prov["meta"]["type"], "source")
        self.assertIn("prisme_type", prov["modifiables"])

    def test_erreurs(self):
        r = self.post("/api/provenance", {"path": str(self.note), "champs": {"prisme_publie_le": "hier"}})
        self.assertEqual(r.status_code, 400)
        self.assertIn("date attendue", r.get_json()["error"])
        self.assertEqual(self.post("/api/provenance", {"path": str(TMP / "dehors.md"),
                                                       "champs": {}}).status_code, 403)
        self.assertEqual(self.post("/api/provenance", {"path": str(VAULT / "absente.md"),
                                                       "champs": {}}).status_code, 404)

    def test_poser_un_identifiant_seul(self):
        r = self.post("/api/provenance/id", {"path": str(self.note)}).get_json()
        meta = self.meta()
        self.assertEqual(list(meta), ["prisme_id"])                  # rien d'autre n'est ajoute
        self.assertEqual(meta["prisme_id"], r["prisme_id"])
        self.assertEqual(r["content"], self.note.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
