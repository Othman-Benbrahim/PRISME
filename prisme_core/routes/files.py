"""Fichiers du vault : liste, lecture, ecriture, renommage, corbeille, liens."""
import json
import shutil
from pathlib import Path

from flask import Blueprint, jsonify, request

from .. import hooks
from ..config import rd_cfg
from .. import provenance
from ..index import fresh_index, notify_changed
from ..index import search as query
from ..index.resolver import LinkResolver
from ..vault import _path_err, in_trash, safe_path, scoped_dir, snapshot, to_trash, vault_root

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
        contenu = d.get("content", "")
        prov = d.get("provenance") or {}
        if prov:                                # (la note peut avoir ete creee juste avant par /api/files/new)
            # Note produite par une machine : en-tete de provenance, et un identifiant
            # est pose sur chaque note citee (docs/decisions/0012).
            contenu = provenance.estampiller(
                contenu,
                type=str(prov.get("type") or "note"),
                outil=str(prov.get("outil") or ""),
                genere_par=str(prov.get("genere_par") or provenance.decrire_modele(rd_cfg())),
                preset=str(prov.get("preset") or ""),
                sources=provenance.sources_vers_ids(prov.get("sources") or []),
                parent=str(prov.get("parent") or ""),
                extra={k: v for k, v in prov.items() if k.startswith(provenance.PREFIX)})
        snap = snapshot(p)                      # version precedente -> .trash/versions/
        p.write_text(contenu, encoding="utf-8")
        notify_changed(p)
        incidents = hooks.emit("note_created" if created else "note_saved", path=str(p), origin="editeur")
        return jsonify({"ok": True, "snapshot": str(snap) if snap else None, "hooks": incidents,
                        "content": contenu if contenu != d.get("content", "") else None})
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
        notify_changed(path)
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
    notify_changed(old, new_path)
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
            notify_changed(p)
            return jsonify({"ok": True, "trashed": False})
        dest = to_trash(p)
        notify_changed(p)
        incidents = hooks.emit("note_deleted", path=str(p), origin="editeur")
        return jsonify({"ok": True, "trashed": True, "trash_path": str(dest), "hooks": incidents})
    except Exception as e: return jsonify({"error": str(e)}), 500

def _scope_arg():
    """Parametre dir : None pour tout le vault, sinon un sous-dossier du vault."""
    raw = request.args.get("dir")
    scoped = scoped_dir(raw)
    return None if scoped == str(vault_root()) else scoped


@bp.route("/api/files/graph", methods=["GET"])
def files_graph():
    scope = _scope_arg()
    return jsonify(query.graph(fresh_index(), scope))


@bp.route("/api/files/backlinks", methods=["GET"])
def backlinks():
    file_path = request.args.get("path", "")
    scope = _scope_arg()
    if not file_path:
        return jsonify({"backlinks": []})
    target = str(safe_path(file_path))
    return jsonify({"backlinks": query.backlinks(fresh_index(), target, scope)})


@bp.route("/api/files/find", methods=["GET"])
def find_file():
    """Trouve un .md a partir d'une reference brute, avec la meme resolution que l'index."""
    ref = request.args.get("name", "").strip()
    src = request.args.get("from", "").strip()
    if not ref:
        return jsonify({"error": "Référence vide"}), 400
    if src:
        src = str(safe_path(src))
    idx = fresh_index()
    resolved = LinkResolver(query.all_paths(idx)).resolve(ref, src or None)
    if not resolved or not Path(resolved).is_file():
        return jsonify({"error": "Fichier introuvable : " + ref}), 404
    return jsonify({"path": resolved, "content": Path(resolved).read_text(encoding="utf-8", errors="replace")})


@bp.route("/api/provenance", methods=["GET"])
def note_provenance():
    """Provenance de la note demandee, avec ses sources resolues."""
    p = safe_path(request.args.get("path", ""))
    idx = fresh_index()
    meta = {k: v for k, v in query.note_meta(idx, str(p)).items() if v not in (None, "", "[]")}
    # L'en-tete du fichier fait foi : l'index ne stocke qu'une partie des champs
    entete = {k.replace(provenance.PREFIX, "", 1): v
              for k, v in provenance.lire(p).items() if k.startswith(provenance.PREFIX)}
    meta.update(entete)
    meta.setdefault("sources", [])
    sources = meta.get("sources") or []
    if isinstance(sources, str):
        try:
            sources = json.loads(sources)
        except ValueError:
            sources = [sources]
    resolues = []
    for ref in sources:
        note = query.by_prisme_id(idx, ref)
        resolues.append({"ref": ref, "path": note["path"], "name": note["name"]} if note
                        else {"ref": ref, "path": None, "name": ref})
    parent = query.by_prisme_id(idx, meta.get("parent"))
    return jsonify({
        "path": str(p),
        # « generee » = un modele est intervenu ; un outil seul peut etre une saisie manuelle
        "genere": bool(meta.get("genere_par")),
        "meta": {k: v for k, v in meta.items() if k != "file_id"},
        "sources": resolues,
        "parent": parent,
        "champs_connus": provenance.CHAMPS,
        "modifiables": list(provenance.MODIFIABLES),
        "types": list(provenance.TYPES),
        "etats": list(provenance.ETATS),
    })


@bp.route("/api/provenance", methods=["POST"])
def set_note_provenance():
    """Ecrit ou corrige la provenance d'une note existante (fiche modifiable)."""
    d = request.get_json(silent=True) or {}
    p = safe_path(d.get("path", ""))
    try:
        contenu = provenance.appliquer(p, d.get("champs") or {},
                                       d.get("sources") if "sources" in d else None)
    except provenance.ChampInvalide as e:
        return jsonify({"error": str(e)}), 400
    notify_changed(p)
    hooks.emit("note_saved", path=str(p), origin="provenance")
    return jsonify({"ok": True, "path": str(p), "content": contenu})


@bp.route("/api/provenance/id", methods=["POST"])
def ensure_note_id():
    """Pose un identifiant sur une note (utilise quand on veut la citer)."""
    p = safe_path((request.get_json(silent=True) or {}).get("path", ""))
    ident = provenance.assurer_id(p)
    notify_changed(p)
    return jsonify({"path": str(p), "prisme_id": ident,
                    "content": Path(p).read_text(encoding="utf-8", errors="replace")})
