"""Identite des passages d'une source, d'un import a l'autre (docs/decisions/0016).

Algorithme repris de Studio Litteraire, applique dans cet ordre :
 1. meme position et meme texte ;
 2. texte identique deplace, a condition qu'il soit unique ;
 3. texte retouche a au moins 65 % de ressemblance, avec une avance nette (8 points)
    sur le meilleur rival.
Dans le doute, le passage recoit un nouvel identifiant plutot qu'un rattachement
hasardeux. Les passages anciens sans repreneur sont declares retires.
"""
import uuid
from difflib import SequenceMatcher

SEUIL = 0.65
MARGE = 0.08
FENETRE = 40          # on ne compare un passage qu'aux anciens proches, sinon c'est quadratique


def nouvel_identifiant():
    return "p-" + uuid.uuid4().hex[:8]


def _ressemblance(a, b):
    if not a or not b:
        return 0.0
    if abs(len(a) - len(b)) > max(len(a), len(b)) * 0.6:
        return 0.0                                   # tailles trop differentes
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def reconcilier(anciens, nouveaux):
    """anciens : [{id, empreinte, texte, position}] ; nouveaux : [Passage].
    Renvoie (attributions, retires) ou attributions = [{passage, id, statut}]."""
    libres = list(range(len(anciens)))
    par_empreinte = {}
    for i, a in enumerate(anciens):
        par_empreinte.setdefault(a["empreinte"], []).append(i)

    attributions = [None] * len(nouveaux)
    pris = set()

    # 1. meme position, meme texte
    for j, p in enumerate(nouveaux):
        if j < len(anciens) and anciens[j]["empreinte"] == p.empreinte and j not in pris:
            attributions[j] = {"passage": p, "id": anciens[j]["id"], "statut": "inchange"}
            pris.add(j)

    # 2. texte identique deplace, si l'ancien est unique
    for j, p in enumerate(nouveaux):
        if attributions[j]:
            continue
        candidats = [i for i in par_empreinte.get(p.empreinte, []) if i not in pris]
        if len(candidats) == 1:
            attributions[j] = {"passage": p, "id": anciens[candidats[0]]["id"], "statut": "deplace"}
            pris.add(candidats[0])

    # 3. texte retouche, avec avance nette
    for j, p in enumerate(nouveaux):
        if attributions[j]:
            continue
        scores = []
        for i in libres:
            if i in pris or abs(i - j) > FENETRE:
                continue
            scores.append((_ressemblance(anciens[i]["texte"], p.texte), i))
        scores.sort(reverse=True)
        if scores and scores[0][0] >= SEUIL and (len(scores) == 1 or scores[0][0] - scores[1][0] >= MARGE):
            i = scores[0][1]
            attributions[j] = {"passage": p, "id": anciens[i]["id"], "statut": "modifie"}
            pris.add(i)

    # 4. le reste est nouveau
    for j, p in enumerate(nouveaux):
        if not attributions[j]:
            attributions[j] = {"passage": p, "id": nouvel_identifiant(), "statut": "nouveau"}

    retires = [a for i, a in enumerate(anciens) if i not in pris]
    return attributions, retires


def comptes(attributions, retires):
    out = {"nouveau": 0, "inchange": 0, "deplace": 0, "modifie": 0, "retire": len(retires)}
    for a in attributions:
        out[a["statut"]] += 1
    return out
