"""Formulaires typés : seule la session de l'auteur peut accepter ou modifier."""
from flask import Blueprint, jsonify, request
from ..objets import registre, reglages, types
from ..objets.sources import ObjetInvalide

bp = Blueprint("types_objets", __name__)
PREFIX = "/api/objets"


def catalogue():
    return {"types": types.TYPES, "reglages": reglages.lire(), "schema": 1,
            "signal_source": "Identifiant URL, DOI, arXiv ou ISBN reconnu : 100/100 (forme seulement)",
            "signal_autres": "Aucun signal mécanique défini : validation obligatoire, quel que soit le seuil"}


@bp.route(PREFIX + "/types", methods=["GET"])
def liste_types():
    return jsonify(catalogue())


@bp.route(PREFIX + "/types/reglages", methods=["POST"])
def regler():
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return jsonify(error="Objet JSON attendu"), 400
    try:
        return jsonify(reglages=reglages.enregistrer(d.get("type"), d.get("entree_directe"), d.get("seuil")))
    except (ObjetInvalide, TypeError) as e:
        return jsonify(error=str(e)), 400


@bp.route(PREFIX + "/registre", methods=["GET"])
def liste_objets():
    try:
        return jsonify(objets=registre.lister(request.args.get("type") or None))
    except ObjetInvalide as e:
        return jsonify(error=str(e)), 400


@bp.route(PREFIX + "/registre", methods=["POST"])
def enregistrer():
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return jsonify(error="Objet JSON attendu"), 400
    try:
        if d.get("cle"):
            obj = registre.modifier(d["cle"], d.get("titre", ""), d.get("champs", {}), d.get("raison", ""))
        else:
            obj = registre.creer(d.get("type"), d.get("titre", ""), d.get("champs", {}), raison=d.get("raison", ""))
        return jsonify(objet=obj)
    except ObjetInvalide as e:
        return jsonify(error=str(e)), 400


@bp.route(PREFIX + "/registre/supprimer", methods=["POST"])
def supprimer():
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return jsonify(error="Objet JSON attendu"), 400
    try:
        return jsonify(registre.supprimer(d.get("cle", ""), d.get("raison", "")))
    except ObjetInvalide as e:
        return jsonify(error=str(e)), 400
