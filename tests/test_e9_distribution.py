"""Régressions E9 : frontières de la livraison et lancement sans Python externe."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from commun import ROOT, VAULT, reset_vault
from prisme_core.app import create_app
from prisme_core.routes import security

spec = importlib.util.spec_from_file_location("construction_e9", ROOT / "packaging/construire.py")
construction = importlib.util.module_from_spec(spec)
spec.loader.exec_module(construction)


class TestDistribution(unittest.TestCase):
    def test_l_inventaire_de_la_distribution_suit_le_dossier_plugins(self):
        """Le seul contrôle que la suite de tests ne voyait pas.

        `diagnostic_distribution.ATTENDUS` est vérifié par le **binaire gelé**, pas ici :
        un plugin livré sans y être inscrit passait toute la suite au vert et faisait
        échouer la construction Windows. C'est arrivé — NEXUS-ARCHÊ a fait échouer la CI
        à chacun de ses trois lots, dont deux déjà fusionnés dans `main`, sans qu'aucun
        test ne bronche. Les deux inventaires sont désormais liés.
        """
        from prisme_core.diagnostic_distribution import ATTENDUS
        livres = {d.name for d in (ROOT / "plugins").iterdir()
                  if (d / "manifest.json").is_file()}
        self.assertEqual(ATTENDUS, livres,
                         "inscrivez le plugin dans diagnostic_distribution.ATTENDUS, "
                         "sinon la construction du binaire le refusera")

    def test_le_rapport_de_construction_annonce_le_bon_compte(self):
        """Le rapport dit « dix plugins actifs » en clair : il doit suivre l'inventaire."""
        from prisme_core.diagnostic_distribution import ATTENDUS
        nombres = {9: "neuf", 10: "dix", 11: "onze", 12: "douze", 13: "treize"}
        attendu = "%s plugins actifs" % nombres.get(len(ATTENDUS), len(ATTENDUS))
        source = (ROOT / "packaging" / "construire.py").read_text(encoding="utf-8")
        self.assertIn('"%s"' % attendu, source)

    def test_frontiere_des_fichiers_livres(self):
        for nom in ("plugins/constat/LICENSE", "plugins/constat/ui.js", "plugins/embeddings-locaux/moteur.py",
                    "guides-plugins/calibration.md", "mcp/prisme_mcp.py"):
            with self.subTest(nom=nom):
                self.assertTrue(construction.livrable(nom))
        for nom in (".env", "plugins/rss/.env", "plugins/rss/.env.local", "plugins/constat/node_modules/a.js",
                    "plugins/constat/tests/lancer.mjs", "plugins/rss/__pycache__/a.pyc", "tests/commun.py"):
            with self.subTest(nom=nom):
                self.assertFalse(construction.livrable(nom))

    def test_mcp_gele_utilise_son_executable(self):
        reset_vault()
        client = create_app(with_plugins=False).test_client()
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(sys, "executable", "D:/PRISME/PRISME.exe"):
            r = client.post("/api/agents/mcp", headers={"X-Prisme-Token": security.TOKEN}, json={"nom": "E9"})
        self.assertEqual(r.status_code, 201)
        c = r.get_json()["configuration"]["mcpServers"]["prisme"]
        self.assertEqual(c["command"], "D:/PRISME/PRISME.exe")
        self.assertEqual(c["args"], ["--mcp"])

    def test_lanceur_refuse_de_simuler_python(self):
        with tempfile.TemporaryDirectory() as d:
            profil = Path(d) / "profil"
            r = subprocess.run([sys.executable, str(ROOT / "prisme.py"), "-m", "maigret"],
                               env={**os.environ, "PRISME_DATA_DIR": str(profil)}, capture_output=True, timeout=10)
            self.assertEqual(r.returncode, 2)
            self.assertFalse(profil.exists())

    def test_mcp_ne_charge_pas_le_profil(self):
        with tempfile.TemporaryDirectory() as d:
            profil = Path(d) / "profil"
            r = subprocess.run([sys.executable, str(ROOT / "prisme.py"), "--mcp"],
                               env={**os.environ, "PRISME_DATA_DIR": str(profil), "PYTHONIOENCODING": "cp1252"},
                               input=json.dumps({"jsonrpc": "2.0", "id": "été", "method": "ping"}, ensure_ascii=False) + "\n",
                               capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout), {"jsonrpc": "2.0", "id": "été", "result": {}})
            self.assertFalse(profil.exists())

    def test_osint_gele_ne_relance_pas_prisme_comme_python(self):
        spec = importlib.util.spec_from_file_location("osint_e9", ROOT / "plugins/osint-cx/__init__.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(module.shutil, "which", return_value=None), \
                mock.patch.object(module.sysconfig, "get_path", side_effect=AssertionError("Scripts Python consulté")), \
                mock.patch.object(module.importlib.util, "find_spec", side_effect=AssertionError("Module externe consulté")):
            self.assertEqual(module._social_cli_candidates("auto"), [])


class TestCheminsWindows(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "alias Windows 8.3")
    def test_recherche_et_arbre_acceptent_un_chemin_court(self):
        import ctypes
        from ctypes import wintypes
        from prisme_core.index import fresh_index
        from prisme_core.index import search
        from prisme_core.arbre import parcours
        reset_vault()
        fn = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
        fn.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        fn.restype = wintypes.DWORD
        buf = ctypes.create_unicode_buffer(32768)
        n = fn(str(VAULT), buf, len(buf))
        self.assertGreater(n, 0)
        court = Path(buf.value)
        if str(court).casefold() == str(VAULT).casefold():
            self.skipTest("Les noms courts ne sont pas disponibles sur ce volume")
        idx = fresh_index(VAULT)
        resultats = search.search(idx, "Beta", root_filter=str(court / "sous"))
        self.assertEqual([x["name"] for x in resultats], ["Beta.md"])
        arbre = parcours.construire(idx, "", depart=str(court / "Alpha.md"))
        self.assertIn("Beta.md", [x["nom"] for x in arbre["noeuds"]])


if __name__ == "__main__":
    unittest.main()
