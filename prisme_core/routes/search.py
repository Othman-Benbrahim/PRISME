"""Recherche plein texte et nuage de tags."""
from pathlib import Path

from flask import Blueprint, jsonify, request

from ..config import rd_cfg
from ..search_index import index_refresh

bp = Blueprint("search", __name__)

@bp.route("/api/search", methods=["GET"])
def search_files():
    query = request.args.get("q", "").strip()
    dir_p = request.args.get("dir", "").strip() or rd_cfg().get("workspace", str(Path.home()))
    if len(query) < 2: return jsonify({"results": []})
    results, total = [], 0
    ql = query.lower()
    idx = index_refresh(dir_p)
    for sp in sorted(idx):
        entry = idx[sp]
        if ql not in entry["lower"]: continue
        f = Path(sp)
        matches = []
        for i, line in enumerate(entry["text"].split("\n")):
            if ql in line.lower():
                matches.append({"line": i+1, "text": line[:140].strip()})
                if len(matches) >= 4: break
        try:    rel = str(f.relative_to(Path(dir_p)))
        except Exception: rel = f.name
        results.append({"path": sp, "name": f.name, "rel": rel, "matches": matches})
        total += 1
        if total >= 40: break
    return jsonify({"results": results})

@bp.route("/api/tags", methods=["GET"])
def get_tags():
    dir_p = request.args.get("dir", "").strip() or rd_cfg().get("workspace", str(Path.home()))
    tags = {}
    idx = index_refresh(dir_p)
    for sp in sorted(idx):
        for tag in idx[sp]["tags"]:
            tags.setdefault(tag, []).append(sp)
    return jsonify({"tags": [{"tag": k, "count": len(v), "files": v}
                              for k, v in sorted(tags.items(), key=lambda x: -len(x[1]))]})
