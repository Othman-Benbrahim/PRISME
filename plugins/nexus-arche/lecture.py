"""Lecture assistée : le modèle propose, ce module vérifie (docs/decisions/0039).

Tout le sens de ce fichier tient dans une contrainte : **l'ancrage rendu par le modèle
doit être une citation littérale de la situation**, vérifiée par comparaison de chaînes.

Sans elle, le dispositif s'effondre. NEXUS-ARCHÊ repose sur le test d'ancrage — une carte
sans observation concrète est inactive. Tant que l'auteur fournissait l'observation, le
test avait du mordant : il fallait trouver la chose dans le réel. Si le même modèle
propose la carte *et* rédige l'observation qui la justifie, on ne mesure plus que sa
fluidité : un modèle sait toujours étayer ce qu'il vient de choisir.

En exigeant un extrait exact, le modèle ne peut plus inventer l'observation. Il doit la
**désigner** dans ce que l'auteur a écrit. C'est une garantie faible — il reste libre de
désigner le mauvais passage — mais elle est vérifiable, et elle rend la fabrication
impossible.
"""
import json
import re
import unicodedata

from . import catalogue

MAX_CARTES = 3              # « 2 à 3 candidates, jamais plus » (protocol.md)
MIN_ANCRAGE = 12            # sous ce seuil, « le » ou « projet » passerait pour un ancrage
MAX_SITUATION = 12_000


def _plat(texte):
    """Replie casse, accents, apostrophes et espaces — sans toucher aux mots.

    Le modèle recopie rarement au caractère près : il change une apostrophe droite en
    courbe, coupe une ligne ailleurs. Normaliser ces variations évite de refuser une
    citation exacte pour une raison typographique. Aucun mot n'est ajouté ni retiré :
    une paraphrase reste une paraphrase, et reste refusée.
    """
    t = unicodedata.normalize("NFD", (texte or "").replace("’", "'").replace("‘", "'"))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip().casefold()


def ancrage_litteral(situation, extrait):
    """(ok, raison). L'extrait doit se retrouver tel quel dans la situation."""
    if not extrait or not extrait.strip():
        return False, "ancrage absent"
    if len(extrait.strip()) < MIN_ANCRAGE:
        return False, "ancrage trop court pour être une observation (%d caractères)" % len(extrait.strip())
    if _plat(extrait) not in _plat(situation):
        return False, "ancrage introuvable dans la situation : ce n'est pas une citation"
    return True, ""


CONSIGNE = """Tu assistes une lecture NEXUS-ARCHÊ : identifier les structures invariantes
qui organisent une situation.

Règles absolues :
1. Propose 2 à 3 cartes candidates, JAMAIS plus, choisies dans la liste fournie.
2. Pour chaque carte, l'ancrage doit être un EXTRAIT LITTÉRAL de la situation, recopié
   mot pour mot. Pas de reformulation, pas de résumé, pas de déduction. Si tu ne trouves
   aucun passage à citer, n'propose pas la carte.
3. Pour chaque carte, formule une anti-résonance : ce qui, dans la situation, CONTREDIT
   cette structure. Si rien ne la contredit, dis-le.
4. La coïncidence lexicale n'est pas un ancrage : un « réseau » nommé ne prouve pas
   RÉSEAU. Cite un fait, pas un mot.

Réponds UNIQUEMENT par un objet JSON de cette forme, sans texte autour :
{"cartes": [{"id": "...", "ancrage": "...", "anti_resonance": "..."}]}"""


def _cartes_pour_prompt():
    return "\n".join(
        "- %s (%s) : %s" % (c["id"], c["nom"], c["registre_rationnel"]) for c in catalogue.toutes())


def _extraire_json(texte):
    """Le modèle encadre souvent son JSON de texte ou de balises. On prend l'objet."""
    if not texte:
        raise ValueError("réponse vide")
    m = re.search(r"\{.*\}", texte, re.S)
    if not m:
        raise ValueError("aucun objet JSON dans la réponse")
    return json.loads(m.group(0))


def proposer(ctx, situation, imposees=None):
    """Rend (resultat, erreur). `imposees` force les cartes (tirage aléatoire).

    Le résultat sépare toujours `retenues` et `ecartees` : une carte refusée ne
    disparaît pas, elle est montrée avec le motif du refus. C'est le protocole — « une
    carte sans ancrage est une carte inactive, elle ne disparaît pas ».
    """
    situation = (situation or "").strip()
    if len(situation) < 40:
        return None, "Décrivez la situation en quelques phrases (40 caractères minimum)."
    if len(situation) > MAX_SITUATION:
        return None, "Situation trop longue (%d caractères, maximum %d)." % (len(situation), MAX_SITUATION)

    if imposees:
        consigne = (CONSIGNE + "\n\nCONTRAINTE SUPPLÉMENTAIRE : les cartes sont imposées, "
                    "tu ne les choisis pas. Pour chacune de %s, cherche un ancrage littéral. "
                    "Si tu n'en trouves pas, rends un ancrage vide : la carte sera déclarée "
                    "inactive, ce qui est un résultat et non un échec."
                    % ", ".join(imposees))
    else:
        consigne = CONSIGNE

    texte, erreur = ctx.ai_call(
        [{"role": "system", "content": consigne},
         {"role": "user", "content": "Cartes disponibles :\n%s\n\nSituation :\n%s"
                                     % (_cartes_pour_prompt(), situation)}],
        max_tokens=1200, temperature=0.2, timeout=120)
    if erreur:
        return None, erreur
    try:
        brut = _extraire_json(texte)
    except (ValueError, json.JSONDecodeError) as e:
        return None, "Réponse du modèle illisible : %s" % e

    return trier(situation, brut.get("cartes"), imposees), None


def trier(situation, proposees, imposees=None):
    """Applique les garde-fous. Aucun appel réseau ici : tout est vérifiable hors ligne."""
    retenues, ecartees = [], []
    if not isinstance(proposees, list):
        return {"retenues": [], "ecartees": [],
                "avertissement": "Le modèle n'a pas rendu de liste de cartes."}

    vues, surnombre = set(), False
    for item in proposees:
        if not isinstance(item, dict):
            continue
        ident = str(item.get("id") or "").strip()
        ancrage = str(item.get("ancrage") or "").strip()
        anti = str(item.get("anti_resonance") or "").strip()
        carte = catalogue.par_id(ident)

        if carte is None:
            ecartees.append({"id": ident, "nom": ident or "(sans identifiant)",
                             "motif": "carte inconnue du catalogue"})
            continue
        if ident in vues:
            ecartees.append({"id": ident, "nom": carte["nom"], "motif": "proposée deux fois"})
            continue
        vues.add(ident)
        if imposees and ident not in imposees:
            ecartees.append({"id": ident, "nom": carte["nom"],
                             "motif": "hors des cartes tirées"})
            continue
        if len(retenues) >= MAX_CARTES:
            surnombre = True
            ecartees.append({"id": ident, "nom": carte["nom"],
                             "motif": "au-delà de %d cartes" % MAX_CARTES})
            continue

        ok, raison = ancrage_litteral(situation, ancrage)
        if not ok:
            ecartees.append({"id": ident, "nom": carte["nom"], "motif": raison,
                             "ancrage_refuse": ancrage})
            continue

        retenues.append({"id": ident, "nom": carte["nom"], "glyphe": carte["glyphe"],
                         "question_iris": carte["question_iris"], "ancrage": ancrage,
                         "anti_resonance": anti,
                         "confusions": catalogue.confusions(ident)})

    avert = ""
    if surnombre:
        avert = "Le modèle a proposé plus de %d cartes ; le surplus est écarté." % MAX_CARTES
    elif not retenues and ecartees:
        avert = ("Aucune carte ancrée. Ce n'est pas un échec : la situation ne présente "
                 "peut-être aucune de ces structures de façon observable.")
    return {"retenues": retenues, "ecartees": ecartees, "avertissement": avert}


def questions_de_distinction(retenues):
    """Les critères qui séparent les cartes retenues deux à deux.

    Posés à l'AUTEUR, pas au modèle : c'est lui qui tranche entre SEUIL et
    TRANSFORMATION, critère des références à l'appui.
    """
    ids = [c["id"] for c in retenues]
    out = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            out.extend(catalogue.questions_entre(a, b))
    return out
