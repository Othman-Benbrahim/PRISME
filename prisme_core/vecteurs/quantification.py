"""Comparaison de vecteurs en deux étages, sans dépendance (docs/decisions/0019).

Comparer une requête à 60 000 segments en cosinus flottant prend 0,6 s en Python pur —
mesuré. Trop lent pour une recherche qui doit répondre pendant qu'on tape.

D'où deux étages :

1. **Présélection binaire.** Chaque vecteur est réduit au signe de ses composantes, un
   bit chacune, stocké dans un entier Python. La distance de Hamming s'obtient par
   `(a ^ b).bit_count()`, exécuté en C : **4 ms pour 60 000 segments**, mesuré.
2. **Rescoring flottant** du meilleur millier, en cosinus exact : 3 ms.

La binarisation perd de la finesse, pas l'essentiel : elle sert à écarter les 98 % de
segments sans rapport, et c'est le cosinus exact qui classe ce qui reste. Total mesuré :
environ 15 ms, contre 600 ms en flottant pur, sans numpy ni bibliothèque compilée.
"""
import array
import math
import operator

RESCORING = 400            # candidats repris en cosinus exact apres la preselection


def binariser(vecteur):
    """Signe de chaque composante, un bit par dimension, dans un entier."""
    bits = 0
    for i, x in enumerate(vecteur):
        if x > 0.0:
            bits |= 1 << i
    return bits


def vers_octets(vecteur):
    """Vecteur flottant -> float32 compact, pour le stockage."""
    return array.array("f", vecteur).tobytes()


def depuis_octets(donnees):
    v = array.array("f")
    v.frombytes(donnees)
    return v


def normaliser(vecteur):
    """Vecteur unitaire : le cosinus se ramène alors à un simple produit scalaire."""
    norme = math.sqrt(sum(x * x for x in vecteur))
    if norme <= 0.0:
        return array.array("f", vecteur)
    return array.array("f", [x / norme for x in vecteur])


def produit(a, b):
    return sum(map(operator.mul, a, b))


def preselectionner(bits_requete, bits_segments, combien=RESCORING):
    """Indices des segments les plus proches en Hamming. `bits_segments` : [(cle, bits)]."""
    if not bits_segments:
        return []
    scores = [((bits_requete ^ b).bit_count(), cle) for cle, b in bits_segments]
    scores.sort(key=lambda s: s[0])
    return [cle for _d, cle in scores[:combien]]


def classer(vecteur_requete, candidats):
    """[(cle, cosinus)] trié du plus proche au plus lointain.

    `candidats` : [(cle, vecteur normalisé)]. La requête doit être normalisée aussi.
    """
    out = [(cle, produit(vecteur_requete, v)) for cle, v in candidats]
    out.sort(key=lambda s: -s[1])
    return out


# ── Fusion des deux recherches ──────────────────────────────────────────
K_RRF = 60                 # constante usuelle du Reciprocal Rank Fusion


def fusionner(*classements, k=K_RRF):
    """Reciprocal Rank Fusion : [(cle, score)] trié.

    Chaque classement est une liste de clés, du meilleur au moins bon. Un élément
    gagne 1/(k + rang) par classement où il apparaît. RRF ne compare pas des scores
    d'origines différentes — un BM25 et un cosinus ne sont pas commensurables — il ne
    compare que des rangs, ce qui est exactement ce qu'on sait faire ici.
    """
    scores = {}
    for classement in classements:
        for rang, cle in enumerate(classement, start=1):
            scores[cle] = scores.get(cle, 0.0) + 1.0 / (k + rang)
    return sorted(scores.items(), key=lambda s: -s[1])


def diversifier(elements, cle_groupe, par_groupe=3, total=40):
    """Évite qu'un seul fichier occupe toute la page de résultats.

    `elements` est déjà trié ; on garde l'ordre en plafonnant par groupe.
    """
    vus, out = {}, []
    for e in elements:
        g = cle_groupe(e)
        if vus.get(g, 0) >= par_groupe:
            continue
        vus[g] = vus.get(g, 0) + 1
        out.append(e)
        if len(out) >= total:
            break
    return out
