"""Contrôle d'accès de la surface agent `/api/v1/` (docs/decisions/0018).

Cette surface ne connaît pas le jeton de session du navigateur : un agent présente
sa clé, dans l'en-tête `X-Prisme-Cle` ou en `Authorization: Bearer`. La garde locale
sur l'en-tête `Host` continue de s'appliquer en amont — l'API n'est joignable que
depuis la machine.

`PRISME_NO_AUTH` ne désarme **pas** cette garde. Cette variable existe pour se passer
du jeton de session pendant un essai de l'interface ; si elle ouvrait aussi l'accès
des agents, elle transformerait un confort de développement en trou béant.
"""
from functools import wraps

from flask import g, jsonify, request

from . import cles, journal

PREFIXE_API = "/api/v1/"
ENTETE = "X-Prisme-Cle"


def _refus(message, code, ident=None, nom=None):
    journal.consigner(ident, nom, request.method, request.path, code, message)
    return jsonify({"error": message}), code


def cle_presentee():
    """La clé, quelle que soit la façon dont l'agent la présente."""
    directe = (request.headers.get(ENTETE) or "").strip()
    if directe:
        return directe
    porteur = (request.headers.get("Authorization") or "").strip()
    if porteur.lower().startswith("bearer "):
        return porteur[7:].strip()
    return ""


def controler():
    """Appelée par la garde globale pour toute requête `/api/v1/`.

    Renvoie None si l'accès est accordé — l'identité de l'agent est alors posée dans
    `g.agent` — ou une réponse de refus.
    """
    cle = cle_presentee()
    if not cle:
        return _refus("Clé d'agent absente : en-tête %s ou Authorization: Bearer" % ENTETE, 401)
    ident, info = cles.verifier(cle)
    if ident is None:
        return _refus(info, 403)                  # info porte la raison du refus
    g.agent = {"id": ident, "nom": info["nom"], "droits": list(info.get("droits", []))}
    cles.marquer_utilisation(ident)
    return None


def exige(droit):
    """Décorateur de route : refuse si la clé ne porte pas ce droit."""
    def decorateur(fn):
        @wraps(fn)
        def enveloppe(*a, **kw):
            agent = getattr(g, "agent", None)
            if not agent:
                return _refus("Identité d'agent absente", 401)
            if droit not in agent["droits"]:
                return _refus(
                    "Droit « %s » non accordé à cette clé. Accordez-le dans PRISME, "
                    "onglet Agents." % droit, 403, agent["id"], agent["nom"])
            reponse = fn(*a, **kw)
            code = reponse[1] if isinstance(reponse, tuple) else 200
            journal.consigner(agent["id"], agent["nom"], request.method, request.path, code)
            return reponse
        return enveloppe
    return decorateur
