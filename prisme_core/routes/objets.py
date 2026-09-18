"""Routes des objets conceptuels : balayage, file de validation, objets Source."""
from flask import Blueprint, jsonify, request

from .. import objets
from ..objets import balayage, file as filedattente, sources

bp = Blueprint("objets", __name__)
PREFIX = "/api/objets"


def _erreur(e, code=400):
    return jsonify({"error": str(e)}), code


def _corps():
    return request.get_json(silent=True) or {}


# ── Objets Source ───────────────────────────────────────────────────────
@bp.route(PREFIX + "/sources", methods=["GET"])
def liste_sources():
    statut = request.args.get("statut") or None
    relu = request.args.get("relu")
    relu = None if relu in (None, "") else relu.lower() in ("1", "true", "oui")
    return jsonify({
        "sources": sources.lister(statut=statut, relu=relu, lot=request.args.get("lot") or None),
        "lots": sources.lots(),
        "dossier": sources.DOSSIER,
        "en_file": len(filedattente.lister()),
        "rejets": len(filedattente.rejets()),
    })


@bp.route(PREFIX + "/balayer", methods=["POST"])
def balayer():
    d = _corps()
    try:
        return jsonify(balayage.balayer(dossier=d.get("dossier") or None))
    except (PermissionError, FileNotFoundError) as e:
        return _erreur(e, 403 if isinstance(e, PermissionError) else 404)


@bp.route(PREFIX + "/ia", methods=["POST"])
def proposer_ia():
    d = _corps()
    try:
        resultat = balayage.proposer_par_ia(dossier=d.get("dossier") or None,
                                            limite=int(d.get("limite") or balayage.MAX_NOTES_IA),
                                            note=d.get("note") or None)
    except objets.ObjetInvalide as e:
        return _erreur(e, 404)
    except (PermissionError, FileNotFoundError) as e:
        return _erreur(e, 403 if isinstance(e, PermissionError) else 404)
    except (TypeError, ValueError) as e:
        return _erreur(e)
    return (jsonify(resultat), 400) if resultat.get("error") else jsonify(resultat)


@bp.route(PREFIX + "/relu", methods=["POST"])
def relu():
    d = _corps()
    try:
        return jsonify({"objet": sources.marquer_relu(d.get("cle", ""),
                                                      relu=bool(d.get("relu", True)))})
    except objets.ObjetInvalide as e:
        return _erreur(e, 404)


@bp.route(PREFIX + "/lier", methods=["POST"])
def lier():
    d = _corps()
    try:
        return jsonify({"objet": sources.lier(d.get("cle", ""), d.get("note", ""))})
    except objets.ObjetInvalide as e:
        return _erreur(e, 404)
    except PermissionError as e:
        return _erreur(e, 403)


@bp.route(PREFIX + "/supprimer", methods=["POST"])
def supprimer():
    d = _corps()
    try:
        return jsonify(sources.supprimer(d.get("cle", ""), d.get("raison", "")))
    except objets.ObjetInvalide as e:
        return _erreur(e, 404)


@bp.route(PREFIX + "/statuts", methods=["POST"])
def statuts():
    return jsonify({"mis_a_jour": sources.rafraichir_statuts()})


@bp.route(PREFIX + "/lot/annuler", methods=["POST"])
def annuler_lot():
    try:
        return jsonify(sources.annuler_lot(_corps().get("lot", "")))
    except objets.ObjetInvalide as e:
        return _erreur(e)


@bp.route(PREFIX + "/note", methods=["GET"])
def objets_de_la_note():
    try:
        return jsonify({"objets": balayage.objets_lies_a(request.args.get("path", ""))})
    except PermissionError as e:
        return _erreur(e, 403)


# ── File de validation ──────────────────────────────────────────────────
@bp.route(PREFIX + "/file", methods=["GET"])
def file_liste():
    return jsonify({"entrees": filedattente.lister(), "rejets": filedattente.rejets(),
                    "plafond": filedattente.PLAFOND_PAR_ORIGINE})


@bp.route(PREFIX + "/file/accepter", methods=["POST"])
def file_accepter():
    d = _corps()
    try:
        return jsonify(balayage.accepter(d.get("cle", ""), titre=d.get("titre"),
                                         reference=d.get("reference"),
                                         raison=d.get("raison", "")))
    except objets.ObjetInvalide as e:
        return _erreur(e)


@bp.route(PREFIX + "/file/rejeter", methods=["POST"])
def file_rejeter():
    d = _corps()
    try:
        return jsonify({"rejet": balayage.rejeter_proposition(d.get("cle", ""),
                                                              d.get("raison", ""))})
    except objets.ObjetInvalide as e:
        return _erreur(e, 404)


@bp.route(PREFIX + "/file/fusionner", methods=["POST"])
def file_fusionner():
    d = _corps()
    try:
        return jsonify(balayage.fusionner(d.get("garde", ""), d.get("absorbe", ""),
                                          d.get("raison", "")))
    except objets.ObjetInvalide as e:
        return _erreur(e)


@bp.route(PREFIX + "/file/defusionner", methods=["POST"])
def file_defusionner():
    d = _corps()
    try:
        return jsonify(balayage.defusionner(d.get("garde", ""), d.get("absorbe", "")))
    except objets.ObjetInvalide as e:
        return _erreur(e)


@bp.route(PREFIX + "/rejets/oublier", methods=["POST"])
def oublier_rejet():
    parti = filedattente.oublier_rejet(_corps().get("cle", ""))
    if parti is None:
        return _erreur("Aucun rejet mémorisé pour cette référence", 404)
    return jsonify({"ok": True, "rejet": parti})
