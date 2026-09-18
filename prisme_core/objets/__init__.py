"""Objets conceptuels (docs/decisions/0017, 0021 et 0022).

Premier et seul type implémenté : **Source**, le registre des références citées.
Une référence repérée mécaniquement (URL, DOI, arXiv, ISBN) entre directement dans
le vault avec le statut « non relu » ; une référence seulement déduite par l'IA part
dans la file de validation. Rien n'entre par l'IA sans l'accord de l'auteur.
"""
from . import detection
from . import file
from . import sources
from .balayage import (accepter, balayer, defusionner, fusionner, objets_lies_a,
                       proposer_par_ia, rejeter_proposition)
from .detection import references
from .sources import ObjetInvalide

__all__ = ["detection", "file", "sources", "references", "ObjetInvalide",
           "balayer", "proposer_par_ia", "accepter", "rejeter_proposition",
           "fusionner", "defusionner", "objets_lies_a"]
