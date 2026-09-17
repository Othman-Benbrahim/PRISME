"""Installation et desinstallation de plugins (docs/decisions/0007 et 0008).

Deux temps : inspect() verifie l'archive et renvoie de quoi afficher l'ecran de
confirmation ; install() n'agit que sur un jeton issu d'inspect().
Les permissions du manifest informent l'utilisateur : elles ne confinent pas
le code Python d'un plugin, qui s'execute avec les droits de PRISME.
"""
import hashlib
import io
import json
import shutil
import stat
import time
import uuid
import zipfile
from pathlib import PurePosixPath
from urllib.parse import urlparse

import requests as http

from . import hooks, plugins, secrets
from .paths import DATA_DIR, PLUGINS_DIR

MAX_ZIP = 20 * 1024 * 1024
MAX_UNPACKED = 100 * 1024 * 1024
MAX_MEMBERS = 2000
STAGING = DATA_DIR / "staging"
TRASH = DATA_DIR / "corbeille-plugins"
STAGING_TTL = 3600


class InstallError(Exception):
    pass


# ── Recuperation ────────────────────────────────────────────────────────
def fetch_url(url):
    parsed = urlparse((url or "").strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise InstallError("Seules les adresses https:// sont acceptees")
    try:
        with http.get(url, stream=True, timeout=(10, 60),
                      headers={"User-Agent": "PRISME-plugin-installer"}) as r:
            if urlparse(r.url).scheme != "https":
                raise InstallError("La redirection quitte HTTPS : installation refusee")
            if r.status_code != 200:
                raise InstallError(f"Telechargement refuse : HTTP {r.status_code}")
            declared = int(r.headers.get("Content-Length") or 0)
            if declared > MAX_ZIP:
                raise InstallError("Archive trop volumineuse (20 Mo maximum)")
            chunks, total = [], 0
            for chunk in r.iter_content(64 * 1024):
                total += len(chunk)
                if total > MAX_ZIP:
                    raise InstallError("Archive trop volumineuse (20 Mo maximum)")
                chunks.append(chunk)
            return b"".join(chunks), r.url
    except http.RequestException as e:
        raise InstallError(f"Telechargement impossible : {type(e).__name__}") from e


# ── Verification ────────────────────────────────────────────────────────
def _safe_member(name):
    """Chemin relatif sur, ou None pour un dossier ; leve InstallError sinon."""
    norm = name.replace("\\", "/")
    if norm.startswith("/") or (len(norm) > 1 and norm[1] == ":"):
        raise InstallError(f"Chemin absolu refuse dans l'archive : {name}")
    parts = [p for p in PurePosixPath(norm).parts if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise InstallError(f"Chemin remontant refuse dans l'archive : {name}")
    return parts


def inspect_bytes(data):
    """Verifie une archive. Renvoie un dict (manifest, prefixe, fichiers, sha256...)."""
    if len(data) > MAX_ZIP:
        raise InstallError("Archive trop volumineuse (20 Mo maximum)")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise InstallError("Ce fichier n'est pas une archive ZIP valide") from e
    with zf:
        infos = zf.infolist()
        if len(infos) > MAX_MEMBERS:
            raise InstallError(f"Trop de fichiers dans l'archive ({len(infos)})")
        total, files = 0, []
        for info in infos:
            parts = _safe_member(info.filename)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise InstallError(f"Lien symbolique refuse : {info.filename}")
            if info.is_dir() or not parts:
                continue
            total += info.file_size
            if total > MAX_UNPACKED:
                raise InstallError("Contenu decompresse trop volumineux (100 Mo maximum)")
            files.append(parts)
        if not files:
            raise InstallError("Archive vide")
        # manifest.json a la racine, ou dans un dossier racine unique (archives GitHub)
        prefix = []
        if ["manifest.json"] not in files:
            tops = {f[0] for f in files}
            if len(tops) == 1 and [*tops, "manifest.json"] in [f[:2] for f in files if len(f) == 2]:
                prefix = [tops.pop()]
            else:
                raise InstallError("manifest.json introuvable a la racine de l'archive")
        try:
            manifest = json.loads(zf.read("/".join(prefix + ["manifest.json"])).decode("utf-8"))
        except (KeyError, ValueError, UnicodeDecodeError) as e:
            raise InstallError(f"manifest.json illisible : {e}") from e
    problems = plugins.validate_manifest(manifest)
    if problems:
        raise InstallError("Manifest refuse : " + " ; ".join(problems))
    return {
        "manifest": manifest,
        "prefix": prefix,
        "files": ["/".join(f[len(prefix):]) for f in files if f[:len(prefix)] == prefix],
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "unpacked": total,
    }


def _clean_staging():
    STAGING.mkdir(parents=True, exist_ok=True)
    now = time.time()
    for f in STAGING.iterdir():
        try:
            if now - f.stat().st_mtime > STAGING_TTL:
                f.unlink()
        except OSError:
            pass


def stage(data, source):
    """Verifie puis met l'archive en attente. Renvoie le resume pour l'ecran de confirmation."""
    report = inspect_bytes(data)
    _clean_staging()
    token = uuid.uuid4().hex
    (STAGING / f"{token}.zip").write_bytes(data)
    meta = {"source": source, "sha256": report["sha256"], "prefix": report["prefix"]}
    (STAGING / f"{token}.json").write_text(json.dumps(meta), encoding="utf-8")
    m = report["manifest"]
    existing = plugins.REGISTRY.get(m["id"])
    return {
        "token": token,
        "id": m["id"],
        "name": m.get("name"),
        "version": m.get("version", "?"),
        "author": m.get("author", ""),
        "description": m.get("description", ""),
        "permissions": [{"id": p, "label": plugins.PERMISSIONS[p]} for p in m.get("permissions", [])],
        "secrets": m.get("secrets", []),
        "files": report["files"][:200],
        "file_count": len(report["files"]),
        "size": report["size"],
        "unpacked": report["unpacked"],
        "sha256": report["sha256"],
        "source": source,
        "exists": existing is not None,
        "installed_version": existing.manifest.get("version") if existing else None,
    }


# ── Installation ────────────────────────────────────────────────────────
def _to_trash(directory, plugin_id):
    dest = TRASH / time.strftime("%Y-%m-%d_%H%M%S") / plugin_id
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(directory), str(dest))
    return dest


def install(token, replace=False):
    if not token or not token.isalnum():
        raise InstallError("Jeton d'installation invalide")
    zpath, mpath = STAGING / f"{token}.zip", STAGING / f"{token}.json"
    if not zpath.exists() or not mpath.exists():
        raise InstallError("Installation expiree : recommencez")
    data = zpath.read_bytes()
    meta = json.loads(mpath.read_text(encoding="utf-8"))
    report = inspect_bytes(data)                      # reverifie : le fichier a pu changer
    if report["sha256"] != meta["sha256"]:
        raise InstallError("L'archive a change depuis sa verification")
    pid = report["manifest"]["id"]
    target = PLUGINS_DIR / pid
    existing = plugins.REGISTRY.get(pid)
    if target.exists() and not replace:
        raise InstallError(f"Un plugin '{pid}' est deja installe")

    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    work = PLUGINS_DIR / f".installation-{token}"
    prefix = report["prefix"]
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                parts = _safe_member(info.filename)
                if info.is_dir() or parts[:len(prefix)] != prefix or len(parts) == len(prefix):
                    continue
                dest = work.joinpath(*parts[len(prefix):])
                if work.resolve() not in dest.resolve().parents:
                    raise InstallError(f"Chemin refuse : {info.filename}")
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)
        restart = False
        if target.exists():
            _to_trash(target, pid)
            restart = existing is not None and existing.ctx is not None
        work.rename(target)
    finally:
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)
        for f in (zpath, mpath):
            f.unlink(missing_ok=True)

    plugins.update_state(pid, enabled=True, source=meta["source"], sha256=report["sha256"],
                         tree_sha256=plugins.tree_sha256(target),
                         installed_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                         version=report["manifest"].get("version", "?"))
    if restart:
        # Python ne recharge pas proprement un module : l'ancienne version reste en
        # memoire jusqu'au redemarrage, on la met hors service d'ici la.
        existing.status = "redemarrage"
        existing.error = "Mise a jour installee : redemarrez PRISME"
        hooks.unsubscribe_plugin(pid)
        return {"id": pid, "status": "redemarrage"}
    plugin = plugins.load_one(target)
    return {"id": pid, "status": plugin.status, "error": plugin.error}


def uninstall(plugin_id):
    plugin = plugins.REGISTRY.get(plugin_id)
    if plugin is None or not plugin.dir.exists():
        raise InstallError(f"Plugin inconnu : {plugin_id}")
    loaded = plugin.ctx is not None
    hooks.unsubscribe_plugin(plugin_id)
    plugin.status = "desactive"
    dest = _to_trash(plugin.dir, plugin_id)
    plugins.update_state(plugin_id, _delete=True)
    secrets.forget_plugin(plugin_id)
    plugins.REGISTRY.pop(plugin_id, None)
    return {"id": plugin_id, "trash": str(dest), "restart_advised": loaded}
