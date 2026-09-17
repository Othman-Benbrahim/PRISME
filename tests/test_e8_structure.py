"""Etape E8 : le decoupage du coeur ne change pas le comportement.

Lancement : python -m unittest discover -s tests -v
"""
import unittest
from pathlib import Path

from commun import ROOT, TMP, VAULT, reset_vault

from prisme_core import config  # noqa: E402,F401
from prisme_core.app import create_app  # noqa: E402
from prisme_core.routes import security  # noqa: E402

_TMP = str(TMP)


class E8Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reset_vault()
        cls.app = create_app(with_plugins=False)
        cls.client = cls.app.test_client()
        cls.h = {"X-Prisme-Token": security.TOKEN}

    def get(self, url, **query):
        # query_string : les chemins Windows (espaces, antislash) restent intacts
        return self.client.get(url, headers=self.h, query_string=query)

    def post(self, url, data):
        return self.client.post(url, headers=self.h, json=data)


class TestSecurite(E8Base):
    def test_jeton_obligatoire(self):
        self.assertEqual(self.client.get("/api/config").status_code, 403)
        self.assertEqual(self.get("/api/config").status_code, 200)

    def test_ancien_entete_refuse(self):
        r = self.client.get("/api/config", headers={"X-SB-Token": security.TOKEN})
        self.assertEqual(r.status_code, 403)

    def test_hote_non_local_refuse(self):
        r = self.client.get("/", headers={"Host": "evil.example"})
        self.assertEqual(r.status_code, 403)

    def test_cle_api_masquee(self):
        config.wr_cfg({"api_key": "secret"})
        try:
            self.assertEqual(self.get("/api/config").get_json()["api_key"], "●●●")
        finally:
            config.wr_cfg({"api_key": ""})

    def test_lecture_hors_vault_refusee(self):
        r = self.get("/api/files/read", path=str(Path(_TMP) / "profil" / "config.json"))
        self.assertEqual(r.status_code, 403)


class TestFichiers(E8Base):
    def test_lecture_ecriture_corbeille(self):
        p = VAULT / "Gamma.md"
        self.assertEqual(self.post("/api/files/new", {"name": "Gamma", "dir": str(VAULT)}).status_code, 200)
        self.post("/api/files/save", {"path": str(p), "content": "# Gamma\n"})
        self.assertEqual(self.get("/api/files/read", path=str(p)).get_json()["content"], "# Gamma\n")
        r = self.post("/api/files/delete", {"path": str(p)}).get_json()
        self.assertTrue(r["trashed"])
        self.assertFalse(p.exists())

    def test_recherche_tags_graphe_backlinks(self):
        res = self.get("/api/search", q="mot-unique").get_json()["results"]
        self.assertEqual([r["name"] for r in res], ["Alpha.md"])
        tags = [t["tag"] for t in self.get("/api/tags").get_json()["tags"]]
        self.assertIn("t1", tags)
        g = self.get("/api/files/graph").get_json()
        self.assertEqual(len(g["links"]), 1)
        bl = self.get("/api/files/backlinks", path=str(VAULT / "Alpha.md")).get_json()
        self.assertEqual([b["name"] for b in bl["backlinks"]], ["Beta.md"])


class TestPage(E8Base):
    def test_page_et_ressources(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("<title>PRISME</title>", html)
        for marker in ("PLUGIN_STYLES", "PLUGIN_SCRIPTS", "PLUGIN_HTML", "PLUGIN_TOOLBAR"):
            self.assertNotIn(marker, html)
        # le jeton doit etre installe avant tout autre script du coeur
        self.assertLess(html.index("/static/js/token.js"), html.index("/static/js/helpers.js"))
        for src in ("/static/js/init.js", "/static/css/core.css"):
            with self.client.get(src) as r:
                self.assertEqual(r.status_code, 200, src)

    def test_aucun_fichier_monolithique(self):
        web = ROOT / "prisme_core" / "web"
        for f in list((web / "js").glob("*.js")) + list((web / "css").glob("*.css")):
            self.assertLess(f.stat().st_size, 20_000, f.name)
        self.assertFalse((ROOT / "ui.html").exists())
        self.assertFalse((ROOT / "second_brain.py").exists())


if __name__ == "__main__":
    unittest.main()
