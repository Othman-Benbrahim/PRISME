"""Recherche plein texte, tags et etat de l'index."""
from flask import Blueprint, jsonify, request

from ..index import fresh_index, get_index
from ..index import search as query
from ..vault import scoped_dir, vault_root

bp = Blueprint("search", __name__)


def _scope():
    scoped = scoped_dir(request.args.get("dir"))
    return None if scoped == str(vault_root()) else scoped


@bp.route("/api/search", methods=["GET"])
def search_files():
    text = request.args.get("q", "").strip()
    scope = _scope()
    if len(text) < 2:
        return jsonify({"results": []})
    idx = fresh_index()
    etat_index = {"state": idx.state, "progress": idx.progress}
    # mode=lexical force la recherche par mots ; sinon on tente l'hybride, qui retombe
    # tout seul sur FTS5 si les vecteurs manquent (docs/decisions/0019).
    if request.args.get("mode") == "lexical":
        return jsonify({"results": query.search(idx, text, root_filter=scope),
                        "index": etat_index, "recherche": {"mode": "lexical", "semantique": False}})
    from ..vecteurs.recherche import hybride
    resultats, info = hybride(idx, text, root_filter=scope)
    return jsonify({"results": resultats, "index": etat_index, "recherche": info})


@bp.route("/api/tags", methods=["GET"])
def get_tags():
    return jsonify({"tags": query.tags(fresh_index(), _scope())})


@bp.route("/api/index/status", methods=["GET"])
def index_status():
    return jsonify(get_index().status())


@bp.route("/api/index/rebuild", methods=["POST"])
def index_rebuild():
    idx = get_index()
    started = idx.start_background(rebuild=True)
    return jsonify({"started": started, **idx.status()})
