"""Gestionnaire de plugins : liste, installation, activation, desinstallation, secrets."""
from flask import Blueprint, jsonify, request

from .. import plugin_install, plugins, secrets
from ..api import PERMISSIONS

bp = Blueprint("plugin_manager", __name__)
PREFIX = "/api/plugin-manager"


def _describe(p):
    record = plugins.read_state().get(p.id, {})
    states = secrets.plugin_secret_states(p.id)
    declared = p.manifest.get("secrets", []) if isinstance(p.manifest, dict) else []
    return {
        "id": p.id,
        "name": p.name,
        "version": p.manifest.get("version", "?"),
        "description": p.manifest.get("description", ""),
        "author": p.manifest.get("author", ""),
        "status": p.status,
        "error": p.error,
        "modified": p.modified,
        "permissions": [{"id": x, "label": PERMISSIONS.get(x, x)} for x in p.manifest.get("permissions", [])],
        "secrets": [{
            "name": s.get("name"),
            "label": s.get("label", s.get("name")),
            "optional": bool(s.get("optional")),
            "state": states.get(s.get("name"), "vide"),
        } for s in declared if isinstance(s, dict)],
        "source": record.get("source", "dossier local"),
        "sha256": record.get("sha256", ""),
        "installed_at": record.get("installed_at", ""),
    }


def _fail(e, code=400):
    return jsonify({"error": str(e)}), code


@bp.route(PREFIX + "/list", methods=["GET"])
def list_plugins():
    return jsonify({
        "plugins": [_describe(p) for _, p in sorted(plugins.REGISTRY.items())],
        "encryption": secrets.available(),
    })


@bp.route(PREFIX + "/inspect", methods=["POST"])
def inspect():
    try:
        upload = request.files.get("file")
        if upload is not None:
            data = upload.read(plugin_install.MAX_ZIP + 1)
            source = f"fichier : {upload.filename}"
        else:
            url = ((request.get_json(silent=True) or {}).get("url") or "").strip()
            if not url:
                return _fail("Choisissez un fichier ZIP ou indiquez une adresse")
            data, final_url = plugin_install.fetch_url(url)
            source = final_url
        return jsonify(plugin_install.stage(data, source))
    except plugin_install.InstallError as e:
        return _fail(e)


@bp.route(PREFIX + "/install", methods=["POST"])
def install():
    d = request.get_json(silent=True) or {}
    try:
        return jsonify(plugin_install.install(d.get("token", ""), bool(d.get("replace"))))
    except plugin_install.InstallError as e:
        return _fail(e)


@bp.route(PREFIX + "/toggle", methods=["POST"])
def toggle():
    d = request.get_json(silent=True) or {}
    pid, enabled = d.get("id", ""), bool(d.get("enabled"))
    if pid not in plugins.REGISTRY:
        return _fail(f"Plugin inconnu : {pid}", 404)
    plugins.update_state(pid, enabled=enabled)
    p = plugins.activate(pid) if enabled else plugins.deactivate(pid)
    return jsonify(_describe(p))


@bp.route(PREFIX + "/uninstall", methods=["POST"])
def uninstall():
    try:
        return jsonify(plugin_install.uninstall((request.get_json(silent=True) or {}).get("id", "")))
    except plugin_install.InstallError as e:
        return _fail(e, 404)


@bp.route(PREFIX + "/secret", methods=["POST"])
def set_secret():
    d = request.get_json(silent=True) or {}
    p = plugins.REGISTRY.get(d.get("id", ""))
    if p is None:
        return _fail("Plugin inconnu", 404)
    name = d.get("name", "")
    if name not in {s.get("name") for s in p.manifest.get("secrets", [])}:
        return _fail(f"Secret non declare par ce plugin : {name}")
    secrets.set_plugin_secret(p.id, name, (d.get("value") or "").strip())
    return jsonify({"ok": True, "state": secrets.plugin_secret_states(p.id).get(name, "vide"),
                    "encryption": secrets.available()})
