"""Fichiers du vault : liste, lecture, ecriture, renommage, corbeille, liens."""
import shutil
from pathlib import Path

from flask import Blueprint, jsonify, request

from .. import hooks
from ..config import rd_cfg
from ..markdown import extract_link_refs, resolve_ref
from ..vault import _path_err, in_trash, iter_md, safe_path, scoped_dir, snapshot, to_trash, vault_root

bp = Blueprint("files", __name__)

@bp.route("/api/files", methods=["GET"])
def list_files():
    """Contenu d'un dossier. Dans le vault : dossiers et fichiers. Hors du vault :
    dossiers seulement, pour pouvoir choisir un autre espace de travail sans
    exposer les noms de fichiers du reste du disque."""
    root = vault_root()
    raw = request.args.get("path", "").strip()
    p = Path(raw).expanduser() if raw else root
    try:
        p = p.resolve()
        inside = p == root or root in p.parents
        items = sorted(
            [{"name": i.name, "path": str(i), "is_dir": i.is_dir(),
              "is_md": i.suffix.lower() in (".md", ".txt", ".markdown")}
             for i in p.iterdir()
             if not i.name.startswith(".") and (inside or i.is_dir())],
            key=lambda x: (not x["is_dir"], x["name"].lower())
        )
        return jsonify({"path": str(p), "parent": str(p.parent), "items": items,
                        "outside_vault": not inside})
    except PermissionError: return jsonify({"error": "Accès refusé"}), 403
    except (FileNotFoundError, NotADirectoryError): return jsonify({"error": "Dossier introuvable"}), 404
    except OSError as e: return jsonify({"error": str(e)}), 400

@bp.route("/api/files/read", methods=["GET"])
def read_file():
    try:
        p = safe_path(request.args.get("path", ""))
        # errors="replace" : une note en CP-1252 ne doit pas faire echouer la lecture
        return jsonify({"content": p.read_text(encoding="utf-8", errors="replace")})
    except (PermissionError, FileNotFoundError) as e: return _path_err(e)
    except Exception as e: return jsonify({"error": str(e)}), 500

@bp.route("/api/files/save", methods=["POST"])
def save_file():
    d = request.json or {}
    try:
        p = safe_path(d.get("path", ""))
        p.parent.mkdir(parents=True, exist_ok=True)
        created = not p.exists()
        snap = snapshot(p)                      # version precedente -> .trash/versions/
        p.write_text(d.get("content", ""), encoding="utf-8")
        incidents = hooks.emit("note_created" if created else "note_saved", path=str(p), origin="editeur")
        return jsonify({"ok": True, "snapshot": str(snap) if snap else None, "hooks": incidents})
    except (PermissionError, FileNotFoundError) as e: return _path_err(e)
    except Exception as e: return jsonify({"error": str(e)}), 500

@bp.route("/api/files/new", methods=["POST"])
def new_file():
    d = request.json or {}
    name = (d.get("name") or "nouveau.md").strip()
    if any(c in name for c in '\\/:*?"<>|'):
        return jsonify({"error": "Nom de fichier invalide"}), 400
    if not name.endswith(".md"): name += ".md"
    try:
        dir_p = safe_path(d.get("dir") or rd_cfg().get("workspace", ""))
        path  = safe_path(dir_p / name)
    except (PermissionError, FileNotFoundError) as e: return _path_err(e)
    if path.exists(): return jsonify({"error": "Fichier existant"}), 409
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {name.replace('.md','')}\n\n", encoding="utf-8")
        incidents = hooks.emit("note_created", path=str(path), origin="editeur")
        return jsonify({"ok": True, "path": str(path), "hooks": incidents})
    except Exception as e: return jsonify({"error": str(e)}), 500

@bp.route("/api/files/rename", methods=["POST"])
def rename_file():
    d = request.json
    try:
        old = safe_path(d.get("old", ""))
    except (PermissionError, FileNotFoundError) as e: return _path_err(e)
    new_name = (d.get("new_name") or "").strip()
    if not old.exists() or not new_name: return jsonify({"error": "Paramètres invalides"}), 400
    if any(c in new_name for c in '\\/:*?"<>|') or new_name in (".", ".."):
        return jsonify({"error": "Nom de fichier invalide"}), 400
    if old == vault_root():
        return jsonify({"error": "Impossible de renommer la racine de l'espace de travail"}), 400
    new_path = old.parent / new_name
    if new_path.exists():
        return jsonify({"error": "Un élément porte déjà ce nom"}), 409
    try:
        old.rename(new_path)
    except Exception as e: return jsonify({"error": str(e)}), 500
    incidents = hooks.emit("note_renamed", path=str(new_path), old_path=str(old), origin="editeur")
    return jsonify({"ok": True, "new_path": str(new_path), "hooks": incidents})

@bp.route("/api/files/delete", methods=["POST"])
def delete_file():
    """Ne supprime plus : deplace vers <vault>/.trash/AAAA-MM-JJ/.
    Seul un element deja dans la corbeille est reellement efface."""
    try:
        p = safe_path((request.json or {}).get("path", ""))
    except (PermissionError, FileNotFoundError) as e: return _path_err(e)
    if p == vault_root():
        return jsonify({"error": "Impossible de supprimer la racine de l'espace de travail"}), 400
    if not p.exists():
        return jsonify({"error": "Fichier ou dossier introuvable"}), 404
    try:
        if in_trash(p):                      # deja dans la corbeille : suppression definitive
            if p.is_dir(): shutil.rmtree(p)
            else: p.unlink()
            return jsonify({"ok": True, "trashed": False})
        dest = to_trash(p)
        incidents = hooks.emit("note_deleted", path=str(p), origin="editeur")
        return jsonify({"ok": True, "trashed": True, "trash_path": str(dest), "hooks": incidents})
    except Exception as e: return jsonify({"error": str(e)}), 500

@bp.route("/api/files/graph", methods=["GET"])
def files_graph():
    dir_p = scoped_dir(request.args.get("dir"))
    files = sorted(iter_md(dir_p))
    vault_paths = {str(f) for f in files}
    degree = {str(f): 0 for f in files}
    edges, seen = [], set()
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
            for ref in extract_link_refs(content):
                target = resolve_ref(ref, str(f), vault_paths)
                if target and target != str(f):
                    key = tuple(sorted([str(f), target]))
                    if key not in seen:
                        seen.add(key); edges.append({"source": str(f), "target": target})
                    degree[str(f)]   = degree.get(str(f),   0) + 1
                    degree[target]   = degree.get(target,   0) + 1
        except: pass
    nodes = [{"id": str(f), "name": f.stem, "path": str(f),
              "degree": degree.get(str(f), 0),
              "rel": str(f.relative_to(dir_p)) if str(f).startswith(dir_p) else f.name}
             for f in files]
    return jsonify({"nodes": nodes, "links": edges})

@bp.route("/api/files/backlinks", methods=["GET"])
def backlinks():
    file_path = request.args.get("path", "")
    dir_p     = scoped_dir(request.args.get("dir"))
    if not file_path: return jsonify({"backlinks": []})
    try:
        target_resolved = str(Path(file_path).resolve())
    except Exception:
        target_resolved = file_path

    vault_paths = {str(f) for f in iter_md(dir_p)}
    results = []
    for f in sorted(iter_md(dir_p)):
        if str(f) == file_path: continue
        try:
            content = f.read_text(encoding="utf-8")
            refs = extract_link_refs(content)
            matched = None
            for ref in refs:
                resolved = resolve_ref(ref, str(f), vault_paths)
                if not resolved: continue
                try: resolved_norm = str(Path(resolved).resolve())
                except: resolved_norm = resolved
                if resolved_norm == target_resolved:
                    matched = ref; break
            if matched:
                # Cherche une ligne contenant la référence pour le contexte
                ctx = ""
                ml = matched.lower()
                for l in content.split("\n"):
                    if ml in l.lower():
                        ctx = l.strip()[:150]; break
                results.append({"path": str(f), "name": f.name, "ctx": ctx, "ref": matched})
        except: pass
    return jsonify({"backlinks": results})

@bp.route("/api/files/find", methods=["GET"])
def find_file():
    """Trouve un .md à partir d'une référence brute, avec résolution intelligente."""
    ref      = request.args.get("name", "").strip()
    src      = request.args.get("from", "").strip()
    dir_p    = scoped_dir(request.args.get("dir"))
    if not ref: return jsonify({"error": "Référence vide"}), 400
    if src: src = str(safe_path(src))
    try:
        vault_paths = {str(f) for f in iter_md(dir_p)}
        # 1. Si source connue, résoudre depuis là
        if src:
            resolved = resolve_ref(ref, src, vault_paths)
            if resolved:
                return jsonify({"path": resolved, "content": Path(resolved).read_text(encoding="utf-8")})
        # 2. Sinon, tenter une résolution sans contexte source
        resolved = resolve_ref(ref, "", vault_paths)
        if resolved:
            return jsonify({"path": resolved, "content": Path(resolved).read_text(encoding="utf-8")})
        return jsonify({"error": "Fichier introuvable : " + ref}), 404
    except Exception as e: return jsonify({"error": str(e)}), 500
