"""Tirage des cartes — hasard cryptographique, et rien d'autre.

Le tirage aléatoire est, contre l'intuition, le mode le plus rigoureux dès qu'un modèle
entre dans la boucle : c'est **le seul où le modèle ne choisit pas ce qu'il va
justifier**. On tire d'abord, on cherche l'ancrage ensuite. Si aucun ancrage littéral
n'existe, la carte est déclarée inactive — et c'est un résultat, pas un échec.

`secrets` plutôt que `random` : non pour la sécurité, mais parce qu'un générateur
reproductible inviterait à rejouer un tirage jusqu'à obtenir la carte qu'on voulait.
"""
import secrets

from . import catalogue

MODES = {
    1: {"nom": "Simple", "cartes": 1, "positions": [""],
        "question": "La Question IRIS de la carte est le point d'entrée."},
    2: {"nom": "Tension", "cartes": 2, "positions": ["", ""],
        "question": "Quelle est la relation structurelle entre ces deux patterns ? "
                    "Les lire en tension, pas en séquence."},
    3: {"nom": "Constellation", "cartes": 3,
        "positions": ["ce qui tient", "ce qui bouge", "ce qui manque"],
        "question": "Trois positions : ce qui tient, ce qui bouge, ce qui manque."},
}


def tirer(mode):
    """Rend la liste des cartes tirées, avec leur position quand le mode en a."""
    if mode not in MODES:
        raise ValueError("Mode inconnu : %r (1, 2 ou 3)" % mode)
    m = MODES[mode]
    cartes = catalogue.toutes()
    choisies, restantes = [], list(cartes)
    for position in m["positions"]:
        c = restantes.pop(secrets.randbelow(len(restantes)))
        choisies.append({"id": c["id"], "nom": c["nom"], "glyphe": c["glyphe"],
                         "position": position, "question_iris": c["question_iris"]})
    return {"mode": mode, "nom_mode": m["nom"], "question": m["question"],
            "cartes": choisies}
