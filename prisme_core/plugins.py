"""Chargement des plugins et assemblage de la page.

Changement E8 : le CSS et le JS de chaque plugin ne sont plus concatenes dans
la page. Chaque plugin est servi comme fichier distinct et charge par sa
propre balise : une erreur dans un plugin ne fait tomber que ce plugin.
"""
import html
import importlib.util
import json
import os

from flask import Blueprint, abort, send_from_directory

from . import compat
from .envfile import load_env_file
from .paths import PLUGINS_DIR, WEB_DIR

bp = Blueprint("plugin_assets", __name__)

LOADED_PLUGINS = []   # dicts : name, dir, manifest, has_css, has_js, ui_html


def load_plugins(flask_app, cfg_reader):
    """Decouvre et charge les plugins du dossier plugins/ (un sous-dossier = un plugin)."""
    compat.install()
    if not PLUGINS_DIR.exists():
        return
    for pdir in sorted(PLUGINS_DIR.iterdir()):
        if not pdir.is_dir() or pdir.name.startswith(("_", ".")):
            continue
        manifest_p = pdir / "manifest.json"
        if not manifest_p.exists():
            print(f"  ! Plugin '{pdir.name}' : pas de manifest.json, ignore")
            continue
        try:
            manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  x Plugin '{pdir.name}' : manifest invalide ({e})")
            continue

        load_env_file(pdir / ".env")
        for key in manifest.get("env", []):
            if not os.getenv(key):
                print(f"  ! Plugin '{pdir.name}' : variable manquante : {key}")

        init_p = pdir / "__init__.py"
        if init_p.exists():
            try:
                spec = importlib.util.spec_from_file_location(f"plugins.{pdir.name}", init_p)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    mod.register(flask_app, cfg_reader)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"  x Plugin '{pdir.name}' : erreur Python ({e}), UI desactivee")
                continue

        ui_html = pdir / "ui.html"
        LOADED_PLUGINS.append({
            "name": manifest.get("name", pdir.name),
            "dir": pdir.name,
            "manifest": manifest,
            "has_css": (pdir / "ui.css").exists(),
            "has_js": (pdir / "ui.js").exists(),
            "ui_html": ui_html.read_text(encoding="utf-8") if ui_html.exists() else "",
        })
        print(f"  + Plugin charge : {pdir.name} ({manifest.get('name', '?')})")


@bp.route("/plugins/<name>/<asset>")
def plugin_asset(name, asset):
    """Sert ui.css / ui.js d'un plugin CHARGE uniquement."""
    if asset not in ("ui.css", "ui.js"):
        abort(404)
    if not any(p["dir"] == name for p in LOADED_PLUGINS):
        abort(404)
    return send_from_directory(PLUGINS_DIR / name, asset)


def _attr(value):
    return html.escape(str(value or ""), quote=True)


def assemble_page():
    """Construit la page a partir de web/index.html et des plugins charges."""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    styles, scripts, blocks, btns = [], [], [], []
    for p in LOADED_PLUGINS:
        d = _attr(p["dir"])
        if p["has_css"]:
            styles.append(f'<link rel="stylesheet" href="/plugins/{d}/ui.css" data-plugin="{d}">')
        if p["has_js"]:
            scripts.append(f'<script src="/plugins/{d}/ui.js" data-plugin="{d}"></script>')
        if p["ui_html"]:
            blocks.append(f"<!-- plugin: {_attr(p['name'])} -->\n{p['ui_html']}")
        for b in p["manifest"].get("buttons", []):
            if b.get("panel") == "toolbar":
                btns.append(f'<button class="hbtn" onclick="{_attr(b.get("onclick"))}" '
                            f'title="{_attr(b.get("title"))}">{html.escape(str(b.get("label", "")))}</button>')
    page = page.replace("<!-- PLUGIN_STYLES -->", "\n".join(styles))
    page = page.replace("<!-- PLUGIN_SCRIPTS -->", "\n".join(scripts))
    page = page.replace("<!-- PLUGIN_HTML -->", "\n".join(blocks))
    page = page.replace("<!-- PLUGIN_TOOLBAR_BUTTONS -->", "\n      ".join(btns))
    return page
