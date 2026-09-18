"""Gestion du trousseau d'agents, depuis l'interface (jeton de session).

À ne pas confondre avec `agent_api.py`, qui est la surface utilisée PAR les agents.
Ici, c'est toi qui crées, révoques et relis.
"""
from flask import Blueprint, jsonify, request

from ..agents import cles, journal

bp = Blueprint("agents", __name__)
PREFIX = "/api/agents"


def _erreur(e, code=400):
    return jsonify({"error": str(e)}), code


def _corps():
    return request.get_json(silent=True) or {}


@bp.route(PREFIX + "/cles", methods=["GET"])
def lister():
    return jsonify({"cles": cles.lister(), "droits": list(cles.DROITS),
                    "droits_defaut": list(cles.DROITS_DEFAUT),
                    "comptes": journal.comptes()})


@bp.route(PREFIX + "/cles", methods=["POST"])
def creer():
    d = _corps()
    try:
        ident, cle = cles.creer(d.get("nom", ""), d.get("droits") or cles.DROITS_DEFAUT)
    except cles.CleInvalide as e:
        return _erreur(e)
    journal.consigner(ident, d.get("nom", ""), "CREATION", PREFIX + "/cles", 201,
                      "droits : %s" % ", ".join(cles.par_id(ident)["droits"]))
    # La seule et unique fois ou la cle en clair sort de PRISME.
    return jsonify({"cle": cle, "info": cles.par_id(ident),
                    "avertissement": "Copiez cette clé maintenant : elle ne sera plus affichée."}), 201


@bp.route(PREFIX + "/cles/droits", methods=["POST"])
def droits():
    d = _corps()
    try:
        info = cles.changer_droits(d.get("id", ""), d.get("droits") or [])
    except cles.CleInvalide as e:
        return _erreur(e, 404)
    journal.consigner(info["id"], info["nom"], "DROITS", PREFIX + "/cles/droits", 200,
                      "droits : %s" % ", ".join(info["droits"]))
    return jsonify({"info": info})


@bp.route(PREFIX + "/cles/revoquer", methods=["POST"])
def revoquer():
    try:
        info = cles.revoquer(_corps().get("id", ""))
    except cles.CleInvalide as e:
        return _erreur(e, 404)
    journal.consigner(info["id"], info["nom"], "REVOCATION", PREFIX + "/cles/revoquer", 200)
    return jsonify({"info": info})


@bp.route(PREFIX + "/cles/oublier", methods=["POST"])
def oublier():
    try:
        return jsonify(cles.oublier(_corps().get("id", "")))
    except cles.CleInvalide as e:
        return _erreur(e, 404)


@bp.route(PREFIX + "/journal", methods=["GET"])
def lire_journal():
    try:
        limite = max(1, min(1000, int(request.args.get("limite") or 200)))
    except ValueError:
        limite = 200
    return jsonify({"lignes": journal.lire(limite=limite, cle=request.args.get("cle") or None)})
