"""Configurations pathologiques du Mode 3 — déterministe, sans modèle.

Ce module ne lit pas la situation. Il ne lit que les identifiants des cartes et leurs
positions, et répond à une question de catalogue : *ces définitions-là s'excluent-elles ?*

La table des antagonismes vient de `references/antagonismes.md` du dépôt NEXUS-ARCHÊ
(v0.3.1), portée telle quelle dans `antagonismes.json`. Elle a été écrite pour ce Mode 3,
qui la supposait sans la fournir depuis la v0.2.

**Un antagonisme n'est une contradiction que si les deux structures portent sur le même
objet.** Une équipe peut connaître une CROISSANCE d'effectif pendant qu'une ÉMERGENCE se
produit dans ses pratiques : deux structures incompatibles, aucun paradoxe. Le module ne
peut pas trancher cela — il ne voit pas la situation. Il produit donc un **signal**
accompagné de la question qui le tranche, posée à l'auteur. C'est le même partage que
l'ancrage littéral : le code vérifie le vérifiable, l'auteur juge ce qui demande de
connaître la situation.
"""
import json
from pathlib import Path

from . import catalogue

FICHIER = Path(__file__).with_name("antagonismes.json")
_CACHE = {}

TIENT, BOUGE, MANQUE = "ce qui tient", "ce qui bouge", "ce qui manque"
MEME_OBJET = "Ces deux structures portent-elles sur la même chose ?"


def _charge():
    if not _CACHE:
        d = json.loads(FICHIER.read_text(encoding="utf-8"))
        _CACHE["paires"] = d["paires"]
        _CACHE["source"] = d.get("source", "")
        _CACHE["index"] = {frozenset((p["a"], p["b"])): p for p in d["paires"]}
    return _CACHE


def toutes():
    return list(_charge()["paires"])


def source():
    return _charge()["source"]


def antagonisme(a, b):
    """La paire si les deux cartes s'excluent, sinon None."""
    if not a or not b or a == b:
        return None
    return _charge()["index"].get(frozenset((a, b)))


def voisinage(a, b):
    """Vrai si les cartes sont « de même nature » au sens du §6 des références.

    Définition dérivée : l'une figure dans les « À ne pas confondre avec » de l'autre, et
    elles ne sont pas antagonistes. Les références n'ont eu à écrire un critère de
    séparation que pour des structures assez proches pour être prises l'une pour l'autre ;
    deux structures incompatibles, elles, ne sont pas de même nature.

    C'est la définition la plus fragile du dispositif — elle détourne une relation écrite
    pour un autre usage. Les références la signalent comme telle.
    """
    if not a or not b or a == b or antagonisme(a, b):
        return False
    return b in catalogue.confusions(a) or a in catalogue.confusions(b)


def _nom(ident):
    c = catalogue.par_id(ident)
    return c["nom"] if c else ident


def _couple(a, b):
    return "%s et %s" % (_nom(a), _nom(b))


def detecter(positions):
    """`positions` : {position: id_de_carte} pour les cartes ACTIVES seulement.

    Une carte tirée sans ancrage est déclarée inactive ; sa position est absente de la
    table, et aucune configuration ne peut être prononcée sur elle. Une constellation
    dont deux cartes sont inactives ne dit rien — c'est un résultat, pas un manque.
    """
    tient, bouge, manque = (positions.get(TIENT), positions.get(BOUGE),
                            positions.get(MANQUE))
    signaux = []

    if tient and manque and tient == manque:
        signaux.append({
            "numero": 1, "nom": "Miroir", "cartes": [tient],
            "signal": "La structure stable est identique à la structure absente : "
                      "ce qui tient est ce qui manque.",
            "lecture": "Nommer la contradiction explicitement et appliquer à la même "
                       "carte les Questions IRIS des deux positions. La tension est "
                       "l'information.",
            "question": "En quoi ce qui vous tient est-il aussi ce qui vous manque ?"})

    if tient and bouge and voisinage(tient, bouge):
        signaux.append({
            "numero": 2, "nom": "Immobilité structurelle", "cartes": [tient, bouge],
            "signal": "%s sont assez proches pour que les références aient dû écrire un "
                      "critère de séparation : le mouvement perçu reproduit peut-être ce "
                      "qui est stable." % _couple(tient, bouge),
            "lecture": "Chercher la source de l'illusion de mouvement. Test "
                       "d'anti-résonance renforcé sur la carte en position « ce qui bouge ».",
            "question": "Qu'est-ce qui distingue vraiment ce qui bouge de ce qui tient, "
                        "ici ?",
            "fragile": "Le voisinage est dérivé d'une relation écrite pour un autre usage "
                       "(les critères de confusion). Signal indicatif."})

    a = antagonisme(tient, manque)
    if a:
        signaux.append({
            "numero": 3, "nom": "Lacune active contradictoire", "cartes": [tient, manque],
            "signal": "%s sont structurellement incompatibles : la situation ne peut "
                      "évoluer sans d'abord déstabiliser ce qui la tient."
                      % _couple(tient, manque),
            "lecture": "Formuler explicitement la contradiction, puis envisager le Mode 4 "
                       "— une carte posée sur la tension, pour la tenir sans l'effacer.",
            "question": MEME_OBJET, "fondement": a["fondement"], "statut": a["statut"],
            "axe": a["axe"]})

    # Les trois paires de positions, et non les paires de la liste des cartes : en
    # configuration 1, la même carte occupe « tient » et « manque », et l'énumérer
    # comme deux cartes fait compter DEUX FOIS l'unique antagonisme qui la lie à
    # « bouge ». La configuration 4 se déclarait alors sur un seul antagonisme, et
    # affichait la même paire deux fois — le compte doit porter sur des paires
    # distinctes de cartes.
    vus, incompatibles = set(), []
    for x, y in ((tient, bouge), (bouge, manque), (tient, manque)):
        p = antagonisme(x, y)
        if p is None:
            continue
        cle = frozenset((p["a"], p["b"]))
        if cle in vus:
            continue
        vus.add(cle)
        incompatibles.append(p)

    actives = []
    for c in (tient, bouge, manque):
        if c and c not in actives:
            actives.append(c)
    if len(incompatibles) >= 2:
        signaux.append({
            "numero": 4, "nom": "Tension maximale", "cartes": actives,
            "signal": "Deux des trois paires de la constellation sont incompatibles : "
                      "plusieurs structures qui ne peuvent pas tenir ensemble organisent "
                      "la même situation.",
            "lecture": "Ne pas chercher à résoudre prématurément. Documenter la tension "
                       "telle qu'elle est, puis envisager le Mode 4.",
            "question": MEME_OBJET,
            "paires": [{"cartes": [p["a_nom"], p["b_nom"]], "fondement": p["fondement"]}
                       for p in incompatibles]})
    return signaux


def positions_actives(retenues, tirage_cartes):
    """Croise les cartes tirées (qui portent les positions) et celles qui ont tenu.

    Rend ({position: id}, [positions inactives]). Sans tirage — mode où le modèle
    choisit — il n'y a pas de positions, donc pas de configuration : les quatre
    configurations sont définies sur les positions du Mode 3, pas sur trois cartes
    quelconques.
    """
    gardees = {c["id"] for c in retenues or []}
    actives, inactives = {}, []
    for c in tirage_cartes or []:
        position = (c.get("position") or "").strip()
        if not position:
            continue
        if c.get("id") in gardees:
            actives[position] = c["id"]
        else:
            inactives.append(position)
    return actives, inactives
