"""Accès des agents extérieurs (docs/decisions/0018).

Une API HTTP locale, une clé par agent, des droits par clé, un journal de tout ce qui
passe. Par défaut un agent lit et propose : ses trouvailles atterrissent dans la file
de validation d'E5, et rien n'entre dans le vault sans ton accord. L'écriture directe
existe, mais s'accorde clé par clé.
"""
from . import cles, garde, journal
from .cles import CleInvalide

__all__ = ["cles", "garde", "journal", "CleInvalide"]
