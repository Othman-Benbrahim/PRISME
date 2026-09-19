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

from commun import ROOT, reset_vault
from prisme_core.app import create_app
from prisme_core.routes import security

spec = importlib.util.spec_from_file_location("construction_e9", ROOT / "packaging/construire.py")
construction = importlib.util.module_from_spec(spec)
spec.loader.exec_module(construction)


class TestDistribution(unittest.TestCase):
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
                               env={**os.environ, "PRISME_DATA_DIR": str(profil)},
                               input=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n",
                               capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout), {"jsonrpc": "2.0", "id": 1, "result": {}})
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


if __name__ == "__main__":
    unittest.main()
