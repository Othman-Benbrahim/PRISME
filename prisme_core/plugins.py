"""Registre, chargement et service des plugins (docs/decisions/0007).

- Un sous-dossier de plugins/ = un plugin ; son identifiant est le nom du dossier.
- Les routes d'un plugin sont servies par un aiguilleur unique sous
  /api/plugins/<id>/ : activer ou desactiver un plugin ne demande pas de
  redemarrage, et un plugin installe a chaud est utilisable tout de suite.
- Chaque ui.css / ui.js est servi comme fichier distinct.
- L'etat (actif, source, empreintes) vit dans ~/.prisme/plugins.json.
"""
import hashlib
import html
import importlib.util
import json
import re
import sys
import threading
import time
import traceback
import types

from flask import Blueprint, abort, jsonify, send_from_directory

from . import hooks
from .api import API_VERSION, PERMISSIONS, PluginContext  # noqa: F401 (PERMISSIONS reexporte)
from .envfile import load_env_file
from .paths import DATA_DIR, PLUGINS_DIR, WEB_DIR

bp = Blueprint("plugins", __name__)

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
STATE_FILE = DATA_DIR / "plugins.json"
_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]
_LOCK = threading.RLock()

# Statuts : actif | desactive | erreur | incompatible | redemarrage
REGISTRY = {}


class Plugin:
    def __init__(self, directory, manifest):
        self.id = directory.name
        self.dir = directory
        self.manifest = manifest
        self.status = "desactive"
        self.error = ""
        self.ctx = None
        self.modified = False

    @property
    def name(self):
        return self.manifest.get("name", self.id)

    def has(self, filename):
        return (self.dir / filename).is_file()

    def ui_html(self):
        f = self.dir / "ui.html"
        return f.read_text(encoding="utf-8") if f.is_file() else ""


# ── Etat persistant ─────────────────────────────────────────────────────
def read_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def update_state(plugin_id, **fields):
    with _LOCK:
        state = read_state()
        if fields.get("_delete"):
            state.pop(plugin_id, None)
        else:
            state.setdefault(plugin_id, {}).update(fields)
        STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def tree_sha256(directory):
    """Empreinte du contenu d'un dossier de plugin (hors caches et .env)."""
    h = hashlib.sha256()
    for f in sorted(p for p in directory.rglob("*") if p.is_file()):
        rel = f.relative_to(directory).as_posix()
        if "__pycache__" in rel or rel.endswith(".pyc") or f.name == ".env":
            continue
        h.update(rel.encode("utf-8") + b"\0")
        h.update(f.read_bytes() + b"\0")
    return h.hexdigest()


# ── Manifest ────────────────────────────────────────────────────────────
def validate_manifest(manifest, folder_name=None):
    """Renvoie la liste des problemes (vide si le manifest est valide)."""
    problems = []
    if not isinstance(manifest, dict):
        return ["manifest.json doit contenir un objet JSON"]
    pid = manifest.get("id")
    if not isinstance(pid, str) or not ID_RE.match(pid):
        problems.append("champ 'id' manquant ou invalide (minuscules, chiffres, - et _, 40 caracteres max)")
    elif folder_name is not None and pid != folder_name:
        problems.append(f"l'id '{pid}' ne correspond pas au dossier '{folder_name}'")
    if manifest.get("api_version") != API_VERSION:
        problems.append(f"api_version {manifest.get('api_version')!r} non prise en charge "
                        f"(PRISME attend {API_VERSION}) — plugin ecrit pour Second Brain V1 ?")
    if not isinstance(manifest.get("name"), str) or not manifest.get("name").strip():
        problems.append("champ 'name' manquant")
    unknown = [p for p in manifest.get("permissions", []) if p not in PERMISSIONS]
    if unknown:
        problems.append("permissions inconnues : " + ", ".join(map(str, unknown)))
    for s in manifest.get("secrets", []):
        if not isinstance(s, dict) or not re.match(r"^[A-Z][A-Z0-9_]{0,63}$", str(s.get("name", ""))):
            problems.append(f"secret mal declare : {s!r}")
    if manifest.get("secrets") and "secrets" not in manifest.get("permissions", []):
        problems.append("des secrets sont declares sans la permission 'secrets'")
    return problems


def read_manifest(directory):
    try:
        return json.loads((directory / "manifest.json").read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, "pas de manifest.json"
    except (OSError, ValueError) as e:
        return None, f"manifest illisible : {e}"


# ── Chargement ──────────────────────────────────────────────────────────
def _ensure_namespace():
    if "prisme_plugins" not in sys.modules:
        ns = types.ModuleType("prisme_plugins")
        ns.__path__ = []
        sys.modules["prisme_plugins"] = ns


def _import(plugin):
    """Importe le plugin et appelle register(ctx)."""
    _ensure_namespace()
    load_env_file(plugin.dir / ".env")
    ctx = PluginContext(plugin.id, plugin.name, plugin.dir, plugin.manifest)
    init = plugin.dir / "__init__.py"
    if init.is_file():
        modname = "prisme_plugins." + plugin.id.replace("-", "_")
        spec = importlib.util.spec_from_file_location(
            modname, init, submodule_search_locations=[str(plugin.dir)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[modname] = module
        try:
            spec.loader.exec_module(module)
            if not hasattr(module, "register"):
                raise RuntimeError("__init__.py ne definit pas register(ctx)")
            module.register(ctx)
        except Exception:
            sys.modules.pop(modname, None)
            hooks.unsubscribe_plugin(plugin.id)
            raise
    plugin.ctx = ctx


def load_one(directory):
    """Inscrit un dossier de plugin et le charge s'il est actif. Renvoie le Plugin ou None."""
    if not directory.is_dir() or directory.name.startswith((".", "_")):
        return None
    manifest, err = read_manifest(directory)
    plugin = Plugin(directory, manifest or {})
    with _LOCK:
        REGISTRY[plugin.id] = plugin
    if not ID_RE.match(plugin.id):
        plugin.status, plugin.error = "incompatible", "nom de dossier invalide"
        return plugin
    if err:
        plugin.status, plugin.error = "incompatible", err
        return plugin
    problems = validate_manifest(manifest, directory.name)
    if problems:
        plugin.status, plugin.error = "incompatible", " ; ".join(problems)
        print(f"  x Plugin '{plugin.id}' ignore : {plugin.error}")
        return plugin

    record = read_state().get(plugin.id, {})
    if record.get("tree_sha256"):
        plugin.modified = record["tree_sha256"] != tree_sha256(directory)
        if plugin.modified:
            print(f"  ! Plugin '{plugin.id}' : contenu modifie depuis son installation")
    if record.get("enabled", True) is False:
        plugin.status = "desactive"
        return plugin
    activate(plugin.id)
    return plugin


def activate(plugin_id):
    plugin = REGISTRY.get(plugin_id)
    if plugin is None or plugin.status in ("incompatible", "redemarrage"):
        return plugin
    if plugin.ctx is None:
        try:
            _import(plugin)
        except Exception as e:                                   # noqa: BLE001
            traceback.print_exc()
            plugin.status, plugin.error = "erreur", f"{type(e).__name__}: {e}"
            print(f"  x Plugin '{plugin_id}' : {plugin.error}")
            return plugin
    plugin.status, plugin.error = "actif", ""
    print(f"  + Plugin actif : {plugin_id} ({plugin.name})")
    return plugin


def deactivate(plugin_id):
    plugin = REGISTRY.get(plugin_id)
    if plugin is not None and plugin.status == "actif":
        plugin.status = "desactive"
    return plugin


def is_active(plugin_id):
    plugin = REGISTRY.get(plugin_id)
    return plugin is not None and plugin.status == "actif"


def load_all():
    hooks.set_activity_check(is_active)
    if not PLUGINS_DIR.exists():
        return
    for directory in sorted(PLUGINS_DIR.iterdir()):
        load_one(directory)


def active_plugins():
    return [p for _, p in sorted(REGISTRY.items()) if p.status == "actif"]


# ── Service HTTP ────────────────────────────────────────────────────────
@bp.route("/api/plugins/<pid>/", defaults={"sub": ""}, methods=_METHODS)
@bp.route("/api/plugins/<pid>/<path:sub>", methods=_METHODS)
def dispatch(pid, sub):
    plugin = REGISTRY.get(pid)
    if plugin is None or plugin.status != "actif" or plugin.ctx is None:
        state = plugin.status if plugin else "inconnu"
        return jsonify({"error": f"Plugin {pid} indisponible ({state})"}), 404
    return plugin.ctx._dispatch(sub)


@bp.route("/plugins/<pid>/<asset>")
def plugin_asset(pid, asset):
    """Sert ui.css / ui.js d'un plugin ACTIF uniquement."""
    if asset not in ("ui.css", "ui.js") or not is_active(pid):
        abort(404)
    response = send_from_directory(REGISTRY[pid].dir, asset)
    response.headers["Cache-Control"] = "no-cache"
    return response


def _attr(value):
    return html.escape(str(value or ""), quote=True)


def assemble_page():
    """Construit la page a partir de web/index.html et des plugins actifs."""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    stamp = int(time.time())
    styles, scripts, blocks, btns = [], [], [], []
    for p in active_plugins():
        d = _attr(p.id)
        if p.has("ui.css"):
            styles.append(f'<link rel="stylesheet" href="/plugins/{d}/ui.css?v={stamp}" data-plugin="{d}">')
        if p.has("ui.js"):
            scripts.append(f'<script src="/plugins/{d}/ui.js?v={stamp}" data-plugin="{d}"></script>')
        fragment = p.ui_html()
        if fragment:
            blocks.append(f"<!-- plugin: {d} -->\n{fragment}")
        for b in p.manifest.get("buttons", []):
            if b.get("panel") == "toolbar":
                btns.append(f'<button class="hbtn" data-plugin="{d}" onclick="{_attr(b.get("onclick"))}" '
                            f'title="{_attr(b.get("title"))}">{html.escape(str(b.get("label", "")))}</button>')
    page = page.replace("<!-- PLUGIN_STYLES -->", "\n".join(styles))
    page = page.replace("<!-- PLUGIN_SCRIPTS -->", "\n".join(scripts))
    page = page.replace("<!-- PLUGIN_HTML -->", "\n".join(blocks))
    page = page.replace("<!-- PLUGIN_TOOLBAR_BUTTONS -->", "\n      ".join(btns))
    return page
