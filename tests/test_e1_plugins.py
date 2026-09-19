"""Etape E1 : API des plugins, hooks, gestionnaire, secrets chiffres, gardes du vault."""
import io
import json
import os
import shutil
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from commun import ROOT, TMP, VAULT, FakeCipher, reset_vault

from prisme_core import api, config, hooks, plugin_install, plugins, secrets
from prisme_core.app import create_app
from prisme_core.routes import security

MANIFEST = {"id": "demo", "name": "Demo", "version": "1.0.0", "api_version": 1,
            "permissions": ["vault_write", "secrets"],
            "secrets": [{"name": "DEMO_KEY", "label": "Cle demo"}],
            "buttons": [{"panel": "toolbar", "label": "D", "onclick": "demo()"}]}

INIT = '''
from flask import jsonify, request
CALLS = []

def register(ctx):
    @ctx.route("/echo/<mot>", methods=["GET", "POST"])
    def echo(mot):
        return jsonify({"mot": mot, "methode": request.method})

    @ctx.route("/")
    def racine():
        return jsonify({"racine": True, "secret": ctx.secret("DEMO_KEY")})

    @ctx.route("/ecrire", methods=["POST"])
    def ecrire():
        p = ctx.write_note(request.json["path"], "par le plugin")
        return jsonify({"path": str(p)})

    @ctx.on("note_saved")
    def vu(path, origin, **_):
        CALLS.append((path, origin))
'''


def make_plugin_dir(base, manifest=MANIFEST, init=INIT, js="function demo(){}"):
    d = base / manifest["id"]
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (d / "__init__.py").write_text(init, encoding="utf-8")
    (d / "ui.js").write_text(js, encoding="utf-8")
    (d / "secret.txt").write_text("x", encoding="utf-8")
    return d


def make_zip(manifest=MANIFEST, init=INIT, top="demo-main/", extra=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(top + "manifest.json", json.dumps(manifest))
        zf.writestr(top + "__init__.py", init)
        zf.writestr(top + "ui.js", "function demo(){}")
        for name, data in (extra or {}).items():
            zf.writestr(name, data)
    return buf.getvalue()


class PluginEnv(unittest.TestCase):
    """Dossier de plugins et registre remis a zero pour chaque test."""

    def setUp(self):
        reset_vault()
        self.pdir = TMP / f"plugins-{self._testMethodName}"
        shutil.rmtree(self.pdir, ignore_errors=True)
        self.pdir.mkdir(parents=True)
        self.patches = [mock.patch.object(plugins, "PLUGINS_DIR", self.pdir),
                        mock.patch.object(plugin_install, "PLUGINS_DIR", self.pdir),
                        mock.patch.object(secrets, "BACKEND", FakeCipher())]
        for p in self.patches:
            p.start()
        plugins.REGISTRY.clear()
        plugins.STATE_FILE.unlink(missing_ok=True)
        secrets.VAULT_FILE.unlink(missing_ok=True)
        for event in hooks.EVENTS:
            hooks._SUBSCRIBERS[event].clear()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        plugins.REGISTRY.clear()

    def client(self):
        app = create_app(with_plugins=True)
        c = app.test_client()
        h = {"X-Prisme-Token": security.TOKEN}
        c.get_ = lambda url, **q: c.get(url, headers=h, query_string=q)
        c.post_ = lambda url, data: c.post(url, headers=h, json=data)
        return c

    def status(self, c, url):
        with c.get(url) as r:
            return r.status_code


class TestChargementEtRoutes(PluginEnv):
    def test_dossiers_residuels_ignores(self):
        for nom, cache in (("vide", False), ("cache-seul", True)):
            with self.subTest(nom=nom):
                d = self.pdir / nom
                (d / "sous-dossier").mkdir(parents=True)
                if cache:
                    (d / "__pycache__").mkdir()
                    (d / "__pycache__" / "ancien.pyc").write_bytes(b"cache")
                self.assertIsNone(plugins.load_one(d))
                self.assertNotIn(nom, plugins.REGISTRY)

    def test_code_sans_manifest_reste_incompatible(self):
        d = self.pdir / "incomplet"
        d.mkdir()
        (d / "__init__.py").write_text("", encoding="utf-8")
        p = plugins.load_one(d)
        self.assertEqual(p.status, "incompatible")
        self.assertIn("manifest", p.error)

    def test_routes_prefixees_et_assets(self):
        make_plugin_dir(self.pdir)
        c = self.client()
        self.assertEqual(plugins.REGISTRY["demo"].status, "actif")
        r = c.post_("/api/plugins/demo/echo/bonjour", {}).get_json()
        self.assertEqual(r, {"mot": "bonjour", "methode": "POST"})
        self.assertTrue(c.get_("/api/plugins/demo/").get_json()["racine"])
        self.assertEqual(c.get_("/api/plugins/demo/inconnu").status_code, 404)
        self.assertEqual(c.post_("/api/plugins/demo/", {}).status_code, 405)
        self.assertEqual(c.get("/api/plugins/demo/").status_code, 403)          # jeton exige
        self.assertEqual(self.status(c, "/plugins/demo/ui.js"), 200)
        self.assertEqual(self.status(c, "/plugins/demo/secret.txt"), 404)
        page = c.get("/").get_data(as_text=True)
        self.assertIn('src="/plugins/demo/ui.js', page)
        self.assertIn('onclick="demo()"', page)

    def test_manifest_v1_refuse(self):
        d = self.pdir / "ancien"
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({"name": "Ancien"}))
        (d / "__init__.py").write_text("from second_brain import _ai_call\ndef register(app, rd_cfg): pass\n")
        self.client()
        p = plugins.REGISTRY["ancien"]
        self.assertEqual(p.status, "incompatible")
        self.assertIn("api_version", p.error)

    def test_erreur_python_isolee(self):
        make_plugin_dir(self.pdir)
        broken = dict(MANIFEST, id="casse")
        make_plugin_dir(self.pdir, broken, init="raise ValueError('boum')\n")
        c = self.client()
        self.assertEqual(plugins.REGISTRY["casse"].status, "erreur")
        self.assertIn("boum", plugins.REGISTRY["casse"].error)
        self.assertEqual(plugins.REGISTRY["demo"].status, "actif")
        self.assertEqual(c.get_("/api/plugins/casse/").status_code, 404)

    def test_desactivation_sans_redemarrage(self):
        make_plugin_dir(self.pdir)
        c = self.client()
        r = c.post_("/api/plugin-manager/toggle", {"id": "demo", "enabled": False}).get_json()
        self.assertEqual(r["status"], "desactive")
        self.assertEqual(c.get_("/api/plugins/demo/").status_code, 404)
        self.assertEqual(self.status(c, "/plugins/demo/ui.js"), 404)
        self.assertNotIn("/plugins/demo/ui.js", c.get("/").get_data(as_text=True))
        c.post_("/api/plugin-manager/toggle", {"id": "demo", "enabled": True})
        self.assertEqual(c.get_("/api/plugins/demo/").status_code, 200)

    def test_plugin_desactive_au_demarrage_puis_active(self):
        make_plugin_dir(self.pdir)
        plugins.update_state("demo", enabled=False)
        c = self.client()
        self.assertIsNone(plugins.REGISTRY["demo"].ctx)             # jamais importe
        c.post_("/api/plugin-manager/toggle", {"id": "demo", "enabled": True})
        self.assertEqual(c.get_("/api/plugins/demo/echo/x").get_json()["mot"], "x")


class TestHooksEtPermissions(PluginEnv):
    def test_hook_appele_a_la_sauvegarde(self):
        make_plugin_dir(self.pdir)
        c = self.client()
        import prisme_plugins.demo as mod
        note = VAULT / "Alpha.md"
        r = c.post_("/api/files/save", {"path": str(note), "content": "x"}).get_json()
        self.assertEqual(r["hooks"], [])
        self.assertEqual(mod.CALLS, [(str(note.resolve()), "editeur")])

    def test_ecriture_du_plugin_ne_boucle_pas(self):
        make_plugin_dir(self.pdir)
        c = self.client()
        import prisme_plugins.demo as mod
        c.post_("/api/plugins/demo/ecrire", {"path": str(VAULT / "Alpha.md")})
        self.assertEqual(mod.CALLS, [])
        self.assertEqual((VAULT / "Alpha.md").read_text(encoding="utf-8"), "par le plugin")

    def test_delai_et_erreur_signales(self):
        hooks.set_activity_check(lambda pid: True)
        hooks.subscribe("lent", "note_saved", lambda **_: time.sleep(1))
        hooks.subscribe("faux", "note_saved", lambda **_: 1 / 0)
        called = []
        hooks.subscribe("bon", "note_saved", lambda **kw: called.append(kw["path"]))
        with mock.patch.object(hooks, "TIMEOUT", 0.2):
            incidents = hooks.emit("note_saved", path="p", origin="editeur")
        self.assertEqual([(i["plugin"], i["probleme"]) for i in incidents],
                         [("lent", "delai"), ("faux", "erreur")])
        self.assertEqual(called, ["p"])

    def test_permissions_du_contexte(self):
        ctx = api.PluginContext("x", "X", self.pdir, {"permissions": []})
        with self.assertRaises(api.PluginPermissionError):
            ctx.write_note(VAULT / "n.md", "x")
        with self.assertRaises(api.PluginPermissionError):
            ctx.secret("DEMO_KEY")
        ctx = api.PluginContext("x", "X", self.pdir, MANIFEST)
        with self.assertRaises(api.PluginPermissionError):
            ctx.secret("AUTRE")
        with self.assertRaises(PermissionError):
            ctx.read_note(TMP / "profil" / "config.json")

    def test_secret_coffre_puis_environnement(self):
        ctx = api.PluginContext("demo", "Demo", self.pdir, MANIFEST)
        with mock.patch.dict(os.environ, {"DEMO_KEY": "depuis-env"}):
            self.assertEqual(ctx.secret("DEMO_KEY"), "depuis-env")
            secrets.set_plugin_secret("demo", "DEMO_KEY", "depuis-coffre")
            self.assertEqual(ctx.secret("DEMO_KEY"), "depuis-coffre")
        stored = secrets.VAULT_FILE.read_text(encoding="utf-8")
        self.assertNotIn("depuis-coffre", stored)
        self.assertIn(secrets.PREFIX, stored)

    def test_ia_indisponible_sans_cle_distante(self):
        ctx = api.PluginContext("x", "X", self.pdir, {})
        config.wr_cfg({"base_url": "https://api.example.com/v1", "api_key": ""})
        self.assertIn("Cle d'API manquante", ctx.ai_unavailable())
        config.wr_cfg({"base_url": "http://localhost:11434/v1"})
        self.assertIsNone(ctx.ai_unavailable())        # Ollama local : pas de cle


class TestInstallation(PluginEnv):
    def inspect(self, c, data):
        return c.post("/api/plugin-manager/inspect", headers={"X-Prisme-Token": security.TOKEN},
                      data={"file": (io.BytesIO(data), "demo.zip")},
                      content_type="multipart/form-data").get_json()

    def test_installation_a_chaud_puis_desinstallation(self):
        c = self.client()
        r = self.inspect(c, make_zip())
        self.assertEqual(r["id"], "demo")
        self.assertEqual([p["id"] for p in r["permissions"]], ["vault_write", "secrets"])
        self.assertEqual(len(r["sha256"]), 64)
        out = c.post_("/api/plugin-manager/install", {"token": r["token"]}).get_json()
        self.assertEqual(out["status"], "actif")
        self.assertEqual(c.get_("/api/plugins/demo/echo/ok").get_json()["mot"], "ok")
        state = plugins.read_state()["demo"]
        self.assertEqual(state["sha256"], r["sha256"])
        self.assertTrue(state["source"].startswith("fichier"))
        # reinstaller le meme id : remplacement, redemarrage requis
        r2 = self.inspect(c, make_zip())
        self.assertTrue(r2["exists"])
        out2 = c.post_("/api/plugin-manager/install", {"token": r2["token"], "replace": True}).get_json()
        self.assertEqual(out2["status"], "redemarrage")
        self.assertEqual(c.get_("/api/plugins/demo/").status_code, 404)
        # desinstallation
        out3 = c.post_("/api/plugin-manager/uninstall", {"id": "demo"}).get_json()
        self.assertTrue(Path(out3["trash"]).exists())
        self.assertFalse((self.pdir / "demo").exists())
        self.assertNotIn("demo", plugins.read_state())

    def test_jeton_invalide_ou_expire(self):
        c = self.client()
        self.assertEqual(c.post_("/api/plugin-manager/install", {"token": "../x"}).status_code, 400)
        self.assertEqual(c.post_("/api/plugin-manager/install", {"token": "abc123"}).status_code, 400)

    def test_archives_piegees_refusees(self):
        cas = {
            "remontee": make_zip(extra={"../evil.py": "x"}),
            "absolu": make_zip(extra={"/etc/evil": "x"}),
            "lecteur": make_zip(extra={"C:/evil": "x"}),
            "sans manifest": make_zip(top="a/", extra={"b/autre.txt": "x"}),
            "id invalide": make_zip(manifest=dict(MANIFEST, id="../x")),
            "api V1": make_zip(manifest={k: v for k, v in MANIFEST.items() if k != "api_version"}),
            "pas un zip": b"ceci n'est pas un zip",
        }
        lien = io.BytesIO()
        with zipfile.ZipFile(lien, "w") as zf:
            zf.writestr("manifest.json", json.dumps(MANIFEST))
            info = zipfile.ZipInfo("lien")
            info.external_attr = (0o120777 << 16)
            zf.writestr(info, "/etc/passwd")
        cas["lien symbolique"] = lien.getvalue()
        for nom, data in cas.items():
            with self.subTest(nom):
                with self.assertRaises(plugin_install.InstallError):
                    plugin_install.inspect_bytes(data)
        self.assertEqual(list(self.pdir.iterdir()), [])

    def test_url_non_https_refusee(self):
        for url in ("http://exemple.org/p.zip", "file:///etc/passwd", "ftp://x/y.zip", ""):
            with self.subTest(url):
                with self.assertRaises(plugin_install.InstallError):
                    plugin_install.fetch_url(url)

    def test_contenu_modifie_detecte(self):
        c = self.client()
        r = self.inspect(c, make_zip())
        c.post_("/api/plugin-manager/install", {"token": r["token"]})
        (self.pdir / "demo" / "ui.js").write_text("alert(1)", encoding="utf-8")
        plugins.REGISTRY.clear()
        self.client()
        self.assertTrue(plugins.REGISTRY["demo"].modified)


class TestSecretsEtConfig(unittest.TestCase):
    def setUp(self):
        reset_vault()

    def test_cle_chiffree_et_migration(self):
        with mock.patch.object(secrets, "BACKEND", None):
            config.wr_cfg({"api_key": "sk-en-clair"})
            self.assertIn("sk-en-clair", config.CFG_F.read_text(encoding="utf-8"))
            self.assertEqual(config.rd_cfg()["key_state"], "clair")
        with mock.patch.object(secrets, "BACKEND", FakeCipher()):
            cfg = config.rd_cfg()                       # migration a la lecture
            self.assertEqual((cfg["api_key"], cfg["key_state"]), ("sk-en-clair", "chiffree"))
            self.assertNotIn("sk-en-clair", config.CFG_F.read_text(encoding="utf-8"))
        with mock.patch.object(secrets, "BACKEND", None):   # autre machine
            cfg = config.rd_cfg()
            self.assertEqual((cfg["api_key"], cfg["key_state"]), ("", "illisible"))
        config.wr_cfg({"api_key": ""})

    def test_cle_jamais_renvoyee(self):
        with mock.patch.object(secrets, "BACKEND", FakeCipher()):
            config.wr_cfg({"api_key": "sk-secrete-123456"})
            c = create_app(with_plugins=False).test_client()
            h = {"X-Prisme-Token": security.TOKEN}
            for url in ("/api/config", "/api/test", "/api/setup/state"):
                self.assertNotIn("sk-secrete", c.get(url, headers=h).get_data(as_text=True), url)
            c.post("/api/config", headers=h, json={"api_key": "●●●", "model": "m2"})
            self.assertEqual(config.rd_cfg()["api_key"], "sk-secrete-123456")
            config.wr_cfg({"api_key": ""})

    def test_config_v1_en_page_de_code_locale(self):
        config.CFG_F.write_bytes(json.dumps({"workspace": "C:/Notes/Écrits"}, ensure_ascii=False).encode("cp1252"))
        self.assertEqual(config.rd_cfg()["workspace"], "C:/Notes/Écrits")
        reset_vault()

    @unittest.skipUnless(os.name == "nt", "DPAPI n'existe que sous Windows")
    def test_dpapi_reel(self):
        self.assertTrue(secrets.available())
        stored = secrets.protect("valeur-test-é")
        self.assertTrue(stored.startswith(secrets.PREFIX))
        self.assertEqual(secrets.reveal(stored), ("valeur-test-é", "chiffree"))


class TestGardesDuVault(unittest.TestCase):
    def setUp(self):
        reset_vault()
        self.c = create_app(with_plugins=False).test_client()
        self.h = {"X-Prisme-Token": security.TOKEN}

    def get(self, url, **q):
        return self.c.get(url, headers=self.h, query_string=q)

    def test_explorateur_hors_vault_dossiers_seulement(self):
        (TMP / "dehors").mkdir(exist_ok=True)
        (TMP / "dehors" / "prive.md").write_text("x")
        (TMP / "dehors" / "sousdossier").mkdir(exist_ok=True)
        r = self.get("/api/files", path=str(TMP / "dehors")).get_json()
        self.assertTrue(r["outside_vault"])
        self.assertEqual([i["name"] for i in r["items"]], ["sousdossier"])
        r = self.get("/api/files").get_json()
        self.assertFalse(r["outside_vault"])
        self.assertIn("Alpha.md", [i["name"] for i in r["items"]])

    def test_parametre_dir_hors_vault_refuse(self):
        for url in ("/api/search", "/api/tags", "/api/files/graph", "/api/files/backlinks"):
            with self.subTest(url):
                self.assertEqual(self.get(url, dir=str(TMP), q="xx", path="a").status_code, 403)
        r = self.c.post("/api/ai/folder", headers=self.h, json={"dir": str(TMP)})
        self.assertIn(r.status_code, (400, 403))

    def test_renommage_protege(self):
        for nom in ("..", "."):
            r = self.c.post("/api/files/rename", headers=self.h,
                            json={"old": str(VAULT / "Alpha.md"), "new_name": nom})
            self.assertEqual(r.status_code, 400)


class TestPluginsLivres(PluginEnv):
    """Les plugins livres avec le depot se chargent tous avec l'API v1."""

    def setUp(self):
        super().setUp()
        shutil.rmtree(self.pdir)
        shutil.copytree(ROOT / "plugins", self.pdir,
                        ignore=shutil.ignore_patterns("__pycache__", ".env"))

    def test_tous_actifs(self):
        c = self.client()
        statuts = {pid: (p.status, p.error) for pid, p in plugins.REGISTRY.items()}
        attendus = {"arxiv", "context", "duckduckgo", "osint-cx",
                    "prompts", "rss", "embeddings-locaux", "constat"}
        # Calibration est une livraison séparée, éventuellement déjà installée.
        if (self.pdir / "calibration" / "manifest.json").is_file():
            attendus.add("calibration")
        self.assertEqual(set(statuts), attendus)
        for pid, (status, error) in statuts.items():
            self.assertEqual(status, "actif", f"{pid} : {error}")
        page = c.get("/").get_data(as_text=True)
        for pid in statuts:
            self.assertIn(f'/plugins/{pid}/ui.js', page)

    def test_reste_de_livraison_ne_cree_pas_de_plugin(self):
        # Reproduit le cache laissé après retrait des fichiers d'une livraison.
        d = self.pdir / "reste-livraison" / "__pycache__"
        d.mkdir(parents=True)
        (d / "ancien.pyc").write_bytes(b"cache")
        self.test_tous_actifs()

    def test_routes_migrees(self):
        c = self.client()
        prompts = c.get_("/api/plugins/prompts/list").get_json()
        self.assertTrue(prompts["prompts"])
        self.assertTrue((TMP / "profil" / "plugins" / "prompts").is_dir())
        files = c.get_("/api/plugins/context/list").get_json()
        self.assertEqual(files["count"], 2)
        self.assertEqual(c.get_("/api/plugins/context/list", dir=str(TMP)).status_code, 403)
        built = c.post_("/api/plugins/context/build", {"paths": [str(VAULT / "Alpha.md")], "depth": 1}).get_json()
        self.assertEqual(built["files_count"], 2)
        self.assertEqual(c.post_("/api/plugins/context/build", {"paths": [str(TMP / "x.md")]}).status_code, 403)
        self.assertEqual(c.get_("/api/plugins/rss/list").get_json()["count"], 0)
        self.assertTrue(c.get_("/api/plugins/osint-cx/ping").get_json()["ok"])

    def test_secret_osint_depuis_le_coffre(self):
        self.client()
        import prisme_plugins.osint_cx as osint
        self.assertEqual(osint._x_token(), "")
        secrets.set_plugin_secret("osint-cx", "X_BEARER_TOKEN", "jeton-xyz")
        self.assertEqual(osint._x_token(), "jeton-xyz")
        self.assertEqual(osint._x_headers()["Authorization"], "Bearer jeton-xyz")


if __name__ == "__main__":
    unittest.main()
