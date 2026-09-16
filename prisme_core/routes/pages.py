"""Page principale et liste des plugins charges."""
from flask import Blueprint, Response, jsonify

from ..plugins import LOADED_PLUGINS, assemble_page

bp = Blueprint("pages", __name__)


@bp.route("/")
def index():
    # Reassemblee a chaque chargement : modifier web/ puis rafraichir suffit.
    return Response(assemble_page(), mimetype="text/html")


@bp.route("/api/plugins", methods=["GET"])
def list_plugins():
    """Liste les plugins charges (debug et future UI de gestion)."""
    return jsonify({
        "count": len(LOADED_PLUGINS),
        "plugins": [{
            "name": p["name"],
            "dir": p["dir"],
            "description": p["manifest"].get("description", ""),
            "version": p["manifest"].get("version", "?"),
            "buttons": p["manifest"].get("buttons", []),
        } for p in LOADED_PLUGINS]
    })
