"""Objets conceptuels : Sources, Décisions, Hypothèses, Prédictions, Entités et Tâches.

La file de validation est commune. Voir types.py pour le contrat E11 ;
registre.py pour les notes typées ; sources.py pour le registre bibliographique.
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
