"""Seuils par type : un score n'autorise rien sans signal mécanique défini."""
from ..config import rd_cfg, wr_cfg
from .sources import ObjetInvalide
from .types import TYPES


def lire():
    stockes = rd_cfg().get("objets_types", {})
    if not isinstance(stockes, dict):
        stockes = {}
    return {t: {"entree_directe": t == "source", "seuil": 100,
                **(stockes.get(t) if isinstance(stockes.get(t), dict) else {})}
            for t in ("source", *TYPES)}


def enregistrer(type_objet, entree_directe, seuil):
    if type_objet not in ("source", *TYPES):
        raise ObjetInvalide("Type inconnu")
    if not isinstance(entree_directe, bool):
        raise ObjetInvalide("Entrée directe : booléen attendu")
    if isinstance(seuil, bool) or not isinstance(seuil, int) or not 0 <= seuil <= 100:
        raise ObjetInvalide("Seuil : entier de 0 à 100 attendu")
    reglages = lire()
    reglages[type_objet] = dict(entree_directe=entree_directe, seuil=seuil)
    wr_cfg({"objets_types": reglages})
    return reglages


def autorise_source(reference):
    from .detection import cle_de
    regle = lire()["source"]
    return bool(regle["entree_directe"] and cle_de(reference) and 100 >= regle["seuil"])
