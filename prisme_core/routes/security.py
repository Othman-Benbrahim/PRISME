"""Garde locale : en-tete Host + jeton de session sur /api/."""
import os
import uuid

from flask import Blueprint, jsonify, request

bp = Blueprint("security", __name__)

TOKEN   = uuid.uuid4().hex

NO_AUTH = os.getenv("PRISME_NO_AUTH") == "1"

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", ""}

# Surface reservee aux agents : authentifiee par cle, jamais par le jeton de session.
AGENTS_PREFIX = "/api/v1/"

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
    p = request.path or ""
    # Verrou 2 : la surface des agents a sa propre authentification, par cle.
    # Elle passe AVANT le raccourci NO_AUTH : cette variable sert a se passer du
    # jeton de session pendant un essai de l'interface, pas a ouvrir l'API des
    # agents (docs/decisions/0018).
    if p.startswith(AGENTS_PREFIX):
        from ..agents.garde import controler
        return controler()
    if NO_AUTH:
        return None
    # Verrou 3 : jeton obligatoire sur /api/, sauf pour le recuperer.
    if p.startswith("/api/") and p != "/api/token":
        if request.headers.get("X-Prisme-Token") != TOKEN:
            return jsonify({"error": "Jeton absent ou invalide — rechargez la page "
                                     "(Ctrl+Maj+R)."}), 403
    return None
