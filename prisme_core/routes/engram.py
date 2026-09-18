"""Routes d'ingestion ENGRAM : inspection, import, registre, controle."""
from flask import Blueprint, jsonify, request

from .. import engram
from ..vault import safe_path, vault_root

bp = Blueprint("engram", __name__)
PREFIX = "/api/engram"


def _erreur(e, code=400):
    return jsonify({"error": str(e)}), code


@bp.route(PREFIX + "/formats", methods=["GET"])
def formats():
    return jsonify({"formats": sorted(engram.formats()),
                    "seuil_partie": engram.seuil_configure(),
                    "dossier_notes": str(vault_root() / "Sources")})


@bp.route(PREFIX + "/inspect", methods=["POST"])
def inspecter():
    d = request.get_json(silent=True) or {}
    try:
        return jsonify(engram.inspecter(d.get("chemin", "")))
    except engram.SourceInvalide as e:
        return _erreur(e)


@bp.route(PREFIX + "/import", methods=["POST"])
def importer():
    d = request.get_json(silent=True) or {}
    dossier = d.get("dossier")
    try:
        if dossier:
            safe_path(dossier)                  # un import ecrit toujours dans le vault
        return jsonify(engram.importer(d.get("chemin", ""), mode=d.get("mode", "reference"),
                                       dossier=dossier, seuil=engram.seuil_configure(),
                                       forcer=bool(d.get("forcer"))))
    except engram.SourceInvalide as e:
        return _erreur(e)


@bp.route(PREFIX + "/sources", methods=["GET"])
def sources():
    return jsonify({"sources": engram.controler()})


@bp.route(PREFIX + "/oublier", methods=["POST"])
def oublier():
    try:
        return jsonify({"ok": True, "source": engram.oublier((request.get_json(silent=True) or {}).get("cle", ""))})
    except engram.SourceInvalide as e:
        return _erreur(e, 404)
