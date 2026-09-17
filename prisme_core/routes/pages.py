"""Page principale et liste des plugins actifs."""
from flask import Blueprint, Response, jsonify

from ..plugins import active_plugins, assemble_page

bp = Blueprint("pages", __name__)


@bp.route("/")
def index():
    # Reassemblee a chaque chargement : modifier web/ puis rafraichir suffit.
    return Response(assemble_page(), mimetype="text/html")


@bp.route("/api/plugins", methods=["GET"])
def list_plugins():
    """Plugins actifs (le detail complet est dans /api/plugin-manager/list)."""
    active = active_plugins()
    return jsonify({
        "count": len(active),
        "plugins": [{
            "id": p.id,
            "name": p.name,
            "description": p.manifest.get("description", ""),
            "version": p.manifest.get("version", "?"),
            "buttons": p.manifest.get("buttons", []),
        } for p in active]
    })
