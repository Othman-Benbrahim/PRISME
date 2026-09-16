"""Garde locale : en-tete Host + jeton de session sur /api/."""
import os
import uuid

from flask import Blueprint, jsonify, request

bp = Blueprint("security", __name__)

TOKEN   = uuid.uuid4().hex

NO_AUTH = os.getenv("PRISME_NO_AUTH") == "1"

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", ""}

@bp.route("/api/token", methods=["GET"])
def api_token():
    """Le navigateur recupere le jeton au chargement. Une page tierce peut
    declencher cet appel mais ne peut PAS en lire la reponse : la politique
    CORS l'en empeche, aucun en-tete Access-Control-Allow-Origin n'est emis."""
    return jsonify({"token": TOKEN})

@bp.before_app_request
def _guard():
    # Verrou 1 : l'en-tete Host doit designer la machine locale.
    # C'est ce qui bloque le DNS rebinding — le navigateur y envoie le
    # domaine de l'attaquant, pas 127.0.0.1.
    host = (request.host or "").rsplit(":", 1)[0].strip("[]").lower()
    if host not in LOCAL_HOSTS:
        return jsonify({"error": "Hôte non autorisé : %s" % host}), 403
    if NO_AUTH:
        return None
    # Verrou 2 : jeton obligatoire sur /api/, sauf pour le recuperer.
    p = request.path or ""
    if p.startswith("/api/") and p != "/api/token":
        if request.headers.get("X-Prisme-Token") != TOKEN:
            return jsonify({"error": "Jeton absent ou invalide — rechargez la page "
                                     "(Ctrl+Maj+R)."}), 403
    return None
