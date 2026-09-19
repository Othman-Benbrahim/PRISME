"""Recherche sémantique (docs/decisions/0019).

Le cœur définit le contrat d'un fournisseur d'embeddings et en fournit deux — une API
compatible OpenAI et Ollama. Un plugin peut en enregistrer d'autres, dont le fournisseur
local ONNX, trop lourd pour le cœur.

Les vecteurs vivent dans une base à part, indexée par empreinte de segment : un
changement de schéma de l'index ne les détruit pas. La recherche fusionne FTS5 et
vecteurs par RRF, et retombe sur FTS5 seul dès que le fournisseur manque à l'appel.
"""
from . import contrat, fournisseurs, magasin, quantification, recherche, vectorisation  # noqa: F401
from .contrat import Fournisseur, VecteurIndisponible, enregistrer
from .recherche import hybride, semantique
from .vectorisation import etat, fournisseur_configure, lancer_en_fond, vectoriser

__all__ = ["contrat", "fournisseurs", "magasin", "quantification", "recherche", "vectorisation",
           "Fournisseur", "VecteurIndisponible", "enregistrer",
           "hybride", "semantique", "etat", "fournisseur_configure", "lancer_en_fond", "vectoriser"]
