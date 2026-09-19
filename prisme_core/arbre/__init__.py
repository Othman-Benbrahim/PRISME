"""Recherche en arbre (docs/decisions/0029).

On part d'une amorce et on se propage par les liens et les backlinks, en décroissant
avec la distance. L'arbre est **montré avant** que l'IA parle : chaque nœud dit
pourquoi il est là et ce qu'il coûte, et l'auteur élague. C'est la règle de 0017
appliquée au contexte — l'IA propose ce qu'elle veut lire, l'auteur valide.
"""
from . import contexte, parcours
from .contexte import assembler, carte, comparer
from .parcours import BUDGET, PROFONDEUR, construire

__all__ = ["contexte", "parcours", "construire", "assembler", "carte", "comparer",
           "BUDGET", "PROFONDEUR"]
