"""ENGRAM — ingestion des sources dans le vault.

Un contrat d'extraction commun, des passages dont l'identifiant survit aux
modifications, une note par source, et l'assurance qu'un reimport ne cree pas
de doublon.
"""
from . import extracteurs  # noqa: F401 (enregistre les extracteurs)
from .contrat import SourceInvalide, formats
from .ingestion import controler, importer, inspecter, lire_registre, oublier, seuil_configure

__all__ = ["SourceInvalide", "formats", "controler", "importer", "inspecter",
           "lire_registre", "oublier", "seuil_configure"]
