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


@bp.route(PREFIX + "/mcp", methods=["POST"])
def mcp():
    """Crée une clé et rend la configuration MCP prête à coller (docs/decisions/0032).

    Une clé, un chemin absolu et une URL, c'est trois choses à assembler sans se tromper,
    et une erreur ne se voit qu'au moment où le client refuse de démarrer. Autant les
    assembler ici : c'est PRISME qui sait où il tourne et où est son adaptateur.
    """
    from ..app import HOST, PORT
    from ..paths import HOME

    d = _corps()
    nom = (d.get("nom") or "Claude Code").strip()
    droits = d.get("droits") or list(cles.DROITS_DEFAUT)
    adaptateur = HOME / "mcp" / "prisme_mcp.py"
    if not adaptateur.is_file():
        return jsonify({"error": "Adaptateur introuvable : %s. Il est livré dans le dossier "
                                 "mcp/ du dépôt, ou à côté de PRISME.exe." % adaptateur}), 404
    try:
        ident, cle = cles.creer(nom, droits)
    except cles.CleInvalide as e:
        return _erreur(e)
    journal.consigner(ident, nom, "CREATION", PREFIX + "/mcp", 201,
                      "clé MCP ; droits : %s" % ", ".join(cles.par_id(ident)["droits"]))
    config = {"mcpServers": {"prisme": {
        "command": "python",
        # Barres obliques même sous Windows : un antislash dans du JSON doit être
        # échappé, et c'est la faute que tout le monde fait en recopiant un chemin.
        "args": [adaptateur.as_posix()],
        "env": {"PRISME_URL": "http://%s:%d" % (HOST, PORT), "PRISME_CLE": cle},
    }}}
    return jsonify({
        "cle": cle, "info": cles.par_id(ident),
        "adaptateur": adaptateur.as_posix(),
        "configuration": config,
        "avertissement": "Cette configuration contient la clé en clair : PRISME ne la "
                         "réaffichera pas. Collez-la maintenant.",
    }), 201


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
