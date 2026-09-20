"""Mise en fiche d'une lecture — deux formats, aucun appel réseau.

Le format est un choix de l'auteur, pas du plugin : la fiche longue garde tout ce qui a
servi à juger (les citations, les refus, les questions restées ouvertes), le bloc
condensé ne garde que ce qui se relit d'un coup d'œil. Les deux portent les mêmes
réserves en tête : une fiche archivée sans elles finirait par se lire comme un verdict.

**Deux notations cohabitent et ne se mélangent jamais.** La chaîne NEXUS est faite des
glyphes des cartes et décrit la *situation* ; la signature MÉMOIRE-Σ décrit la *séance*
d'analyse. Elles partagent des glyphes avec des sens différents — `⊥` vaut SEUIL dans
l'une, LIMITE dans l'autre. La chaîne NEXUS n'est donc jamais soumise au valideur Σ, et
la fiche les sépare par deux titres distincts.
"""
from datetime import datetime

from . import catalogue, configurations, lecture, sigma

DOSSIER = "Lectures NEXUS"
POSITIONS = (configurations.TIENT, configurations.BOUGE, configurations.MANQUE)
FORMATS = {"longue": "Fiche complète", "bloc": "Bloc condensé"}
STATUTS = {
    "descriptif": "Descriptif — décrit une structure observée et ancrée dans des faits",
    "speculatif": "Spéculatif — propose une configuration possible, non confirmée",
    "performatif": "Performatif — agit sur la façon d'habiter la situation",
}
RESERVE = ("Lecture structurelle. Cet outil ne prédit pas, ne prescrit pas, ne "
           "diagnostique pas. Une carte sans ancrage est inactive : elle ne disparaît "
           "pas, elle attend une situation qui lui corresponde.")


def horodatage(maintenant=None):
    return (maintenant or datetime.now()).strftime("%Y%m%d-%H%M%S")


def nom_fichier(maintenant=None):
    return "%s/Lecture-%s.md" % (DOSSIER, horodatage(maintenant))


def chaine_nexus(retenues):
    """Rend (glyphes, transcription) pour les cartes actives.

    C'est la « signature compressée de la situation » du protocole. Elle se calcule,
    elle ne se devine pas : aucun modèle n'intervient ici.

    L'ordre suit les positions quand il y en a — `tient.bouge.manque` est une syntaxe
    positionnelle, pas une liste : une constellation dont on intervertirait les glyphes
    ne dirait pas la même chose.
    """
    ordre = {p: i for i, p in enumerate(POSITIONS)}
    rangs = sorted(range(len(retenues or [])),
                   key=lambda i: (ordre.get((retenues[i].get("position") or "").strip(),
                                            len(POSITIONS)), i))
    cartes = [catalogue.par_id(retenues[i]["id"]) for i in rangs]
    cartes = [c for c in cartes if c]
    return "".join(c["glyphe"] for c in cartes), ".".join(c["mot"] for c in cartes)


def _position(c):
    p = (c.get("position") or "").strip()
    return " — *%s*" % p if p else ""


def _entete(titre, maintenant=None):
    quand = (maintenant or datetime.now()).strftime("%d/%m/%Y à %H:%M")
    return ["# %s" % titre, "", "*%s*" % quand, "", "> %s" % RESERVE, ""]


def _bloc_signature(signature, transcription_sigma):
    if not signature:
        return []
    ligne = "`%s`" % signature
    if transcription_sigma:
        ligne += " — %s" % transcription_sigma
    return ["## Signature MÉMOIRE-Σ de la séance", "",
            "Décrit la **séance d'analyse**, pas la situation. Alphabet MÉMOIRE-Σ, "
            "distinct de celui des cartes.", "", ligne, ""]


def _bloc_configurations(signaux, longue):
    if not signaux:
        return []
    out = ["## Configurations signalées", ""]
    if longue:
        out += ["Une configuration est une **hypothèse**, pas un verdict : elle se "
                "vérifie comme un ancrage. Un antagonisme entre deux cartes ne devient "
                "une contradiction que si les deux structures portent sur le même objet.",
                ""]
    for s in signaux:
        out.append("### %d — %s" % (s["numero"], s["nom"]))
        out += ["", s["signal"], ""]
        if longue:
            if s.get("fondement"):
                out += ["*Fondement (%s)* : %s" % (s.get("statut", ""), s["fondement"]), ""]
            for p in s.get("paires", []):
                out.append("- %s ↮ %s — %s" % (p["cartes"][0], p["cartes"][1], p["fondement"]))
            if s.get("paires"):
                out.append("")
            if s.get("fragile"):
                out += ["*%s*" % s["fragile"], ""]
            out += ["*Lecture recommandée* : %s" % s["lecture"], ""]
        out += ["> **À trancher** : %s" % s["question"], ""]
    return out


def markdown(donnees, format="longue", maintenant=None):
    """Rend le texte de la fiche. `donnees` est ce que l'interface a sous les yeux."""
    if format not in FORMATS:
        raise ValueError("Format inconnu : %r (%s)" % (format, " / ".join(FORMATS)))
    retenues = donnees.get("retenues") or []
    ecartees = donnees.get("ecartees") or []
    signaux = donnees.get("configurations") or []
    statut = STATUTS.get((donnees.get("statut") or "").strip().lower(), "")
    glyphes, transcription = chaine_nexus(retenues)
    longue = format == "longue"

    lignes = _entete("NEXUS-ARCHÊ — lecture", maintenant)

    if glyphes:
        lignes += ["## Chaîne NEXUS", "",
                   "`%s` — %s" % (glyphes, transcription), "",
                   "Alphabet des **cartes** : ce n'est pas une signature MÉMOIRE-Σ.", ""]
    if statut:
        lignes += ["**Statut épistémique** : %s" % statut, ""]

    if donnees.get("mode_nom"):
        lignes += ["## Tirage", "",
                   "%s. Les cartes sont sorties **avant** l'analyse : le modèle n'a pas "
                   "choisi ce qu'il allait justifier." % donnees["mode_nom"], ""]

    if longue and (donnees.get("situation") or "").strip():
        lignes += ["## Situation", "", donnees["situation"].strip(), ""]

    lignes += ["## Cartes actives", ""]
    if not retenues:
        lignes += ["Aucune. La situation ne présente aucune de ces structures de façon "
                   "observable — c'est un résultat, pas un échec.", ""]
    for c in retenues:
        if longue:
            lignes.append("### %s %s%s" % (c.get("glyphe", ""), c.get("nom", ""), _position(c)))
            lignes += ["", "**Ancrage — citation de la situation** : « %s »" % c.get("ancrage", ""), ""]
            if c.get("anti_resonance"):
                lignes += ["**Anti-résonance — ce qui contredit** : %s" % c["anti_resonance"], ""]
            if c.get("question_iris"):
                lignes += ["**Question IRIS** : %s" % c["question_iris"], ""]
        else:
            lignes.append("- %s **%s**%s — « %s »" % (
                c.get("glyphe", ""), c.get("nom", ""), _position(c), c.get("ancrage", "")))
    if not longue and retenues:
        lignes.append("")

    if ecartees:
        lignes += ["## Cartes inactives", ""]
        lignes += ["- %s — %s" % (c.get("nom", ""), c.get("motif", "")) for c in ecartees]
        lignes.append("")

    lignes += _bloc_configurations(signaux, longue)

    distinctions = donnees.get("distinctions") or []
    if longue and distinctions:
        lignes += ["## À trancher vous-même", "",
                   "Ces critères départagent les cartes retenues. Ils sont posés à "
                   "l'auteur, pas au modèle.", ""]
        lignes += ["- %s" % d["critere"] for d in distinctions]
        lignes.append("")

    lignes += _bloc_signature(donnees.get("signature", "").strip(),
                              donnees.get("transcription_sigma", "").strip())

    if longue:
        lignes += ["---", "",
                   "*Cartes : %s*" % catalogue.source(), "",
                   "*Antagonismes : %s*" % configurations.source(), ""]
    return "\n".join(lignes).rstrip() + "\n"


def consolider(donnees):
    """Reconstruit la fiche depuis le catalogue et re-vérifie chaque ancrage.

    Rend (donnees_propres, erreur). Deux raisons de refaire ce travail au moment
    d'écrire plutôt que de recopier ce que l'interface affiche :

    - les noms et glyphes sont relus depuis le catalogue, donc une fiche ne peut pas
      porter un nom de carte qui ne correspond pas à son identifiant ;
    - **les ancrages repassent le test littéral**. Une fiche est ce qui survit à la
      séance ; elle ne doit pas pouvoir contenir une citation qui n'en est pas une.
    """
    situation = (donnees.get("situation") or "").strip()
    retenues, positions = [], {}
    for item in donnees.get("retenues") or []:
        carte = catalogue.par_id(str(item.get("id") or ""))
        if carte is None:
            return None, "Carte inconnue du catalogue : %s" % item.get("id")
        ancrage = str(item.get("ancrage") or "").strip()
        ok, raison = lecture.ancrage_litteral(situation, ancrage)
        if not ok:
            return None, "%s : %s — la fiche n'est pas écrite." % (carte["nom"], raison)
        position = str(item.get("position") or "").strip()
        if position:
            if position not in POSITIONS:
                return None, "Position inconnue : %s" % position
            if position in positions:
                return None, "Deux cartes pour la position « %s »" % position
            positions[position] = carte["id"]
        retenues.append({"id": carte["id"], "nom": carte["nom"], "glyphe": carte["glyphe"],
                         "question_iris": carte["question_iris"], "ancrage": ancrage,
                         "position": position,
                         "anti_resonance": str(item.get("anti_resonance") or "").strip()})

    ecartees = [{"nom": (catalogue.par_id(str(c.get("id") or "")) or {}).get("nom")
                        or str(c.get("nom") or ""),
                 "motif": str(c.get("motif") or "")}
                for c in donnees.get("ecartees") or []]

    propres = {"situation": situation, "retenues": retenues, "ecartees": ecartees,
               "mode_nom": str(donnees.get("mode_nom") or "").strip(),
               "statut": str(donnees.get("statut") or "").strip(),
               "signature": str(donnees.get("signature") or "").strip(),
               "distinctions": lecture.questions_de_distinction(retenues),
               "configurations": configurations.detecter(positions)}
    if propres["signature"]:
        verdict = sigma.valider(propres["signature"])
        if not verdict["ok"]:
            return None, "Signature MÉMOIRE-Σ refusée : %s" % verdict["raison"]
        # Le statut figure déjà dans la chaîne recopiée : ne pas le répéter.
        propres["transcription_sigma"] = verdict["transcription"]
    return propres, None
