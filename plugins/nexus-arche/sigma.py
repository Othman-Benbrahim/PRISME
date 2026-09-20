"""Valideur de signature MÉMOIRE-Σ — pur, hors ligne, sans modèle.

Le modèle propose la chaîne ; ce module dit si elle est licite. C'est le seul
critère formel objectif de tout le plugin : partout ailleurs on juge, ici on vérifie.

La grammaire est celle du SKILL.md de MÉMOIRE-Σ (v1.1.1) :

    ⟦ [1-3 substances] [1-2 opératives] [0-2 modales] ⟧ Statut     — 2 à 6 glyphes

Trois règles, et aucune tolérance : une grammaire qu'on assouplit dès qu'elle refuse
quelque chose cesse d'être un critère.

**La signature décrit la SÉANCE d'analyse, pas la situation analysée.** Les deux
alphabets partagent des glyphes avec des sens distincts — `⊥` est « piste close » ici
et SEUIL dans le catalogue NEXUS. Ne jamais mêler les deux dans une même chaîne.
"""

SUBSTANCES = {
    "⊙": "SOURCE", "◯": "FORME", "Ø": "VIDE", "∿": "MOUVEMENT",
    "⊥": "LIMITE", "✦": "AXE", "◊": "TRACE", "⊛": "NOEUD",
}
OPERATIVES = {
    "⟁": "FRACTURER", "⊗": "LIER", "✶": "RÉVÉLER", "⊜": "SCELLER",
    "⌒": "PLIER", "⥀": "INVERSER", "⟶": "TRANSMETTRE",
}
MODALES = {"↻": "CYCLE", "▲": "INTENSITÉ", "⊘": "NÉGATION", "◐": "CONDITIONNEL", "◌": "SILENCE"}

STATUTS = ("Clos", "Ouvert", "Bifurqué")
OUVRANT, FERMANT = "⟦", "⟧"
MAX_GLYPHES = 6
BORNES = {"S": (1, 3), "O": (1, 2), "M": (0, 2)}
STRATES = {"S": SUBSTANCES, "O": OPERATIVES, "M": MODALES}
NOMS = {"S": "substance", "O": "opérative", "M": "modale"}


def strate(glyphe):
    for code, table in STRATES.items():
        if glyphe in table:
            return code
    return None


def mot(glyphe):
    for table in STRATES.values():
        if glyphe in table:
            return table[glyphe]
    return ""


def _decouper(brut):
    """Rend (glyphes, statut). Accepte « ⟦…⟧ Statut », « ⟦…⟧ » ou la chaîne nue."""
    texte = (brut or "").strip()
    if OUVRANT in texte:
        if FERMANT not in texte.split(OUVRANT, 1)[1]:
            raise ValueError("Délimiteur fermant %s manquant" % FERMANT)
        avant, reste = texte.split(OUVRANT, 1)
        if avant.strip():
            raise ValueError("Texte avant le délimiteur ouvrant : « %s »" % avant.strip())
        corps, apres = reste.split(FERMANT, 1)
        return corps.strip(), apres.strip()
    if FERMANT in texte:
        raise ValueError("Délimiteur ouvrant %s manquant" % OUVRANT)
    return texte, ""


def valider(brut, exiger_statut=True):
    """Rend {ok, raison, glyphes, strates, statut, transcription}.

    `raison` est destinée à être lue par l'auteur : elle dit ce qui cloche, pas
    seulement que ça cloche.
    """
    resultat = {"ok": False, "raison": "", "glyphes": "", "strates": "",
                "statut": "", "transcription": ""}
    try:
        corps, statut = _decouper(brut)
    except ValueError as e:
        resultat["raison"] = str(e)
        return resultat

    glyphes = [g for g in corps if not g.isspace()]
    resultat["glyphes"] = "".join(glyphes)
    if not glyphes:
        resultat["raison"] = "Chaîne vide"
        return resultat

    inconnus = [g for g in glyphes if strate(g) is None]
    if inconnus:
        resultat["raison"] = ("Glyphe hors alphabet MÉMOIRE-Σ : %s. L'alphabet compte "
                              "20 primitives ; un glyphe du catalogue NEXUS n'y a pas sa place."
                              % " ".join(sorted(set(inconnus))))
        return resultat

    codes = "".join(strate(g) for g in glyphes)
    resultat["strates"] = codes

    if len(glyphes) > MAX_GLYPHES:
        resultat["raison"] = "%d glyphes : le maximum est %d" % (len(glyphes), MAX_GLYPHES)
        return resultat

    attendu = "".join(sorted(codes, key="SOM".index))
    if codes != attendu:
        resultat["raison"] = ("Ordre des strates rompu (%s) : les substances viennent en "
                              "premier, puis les opératives, puis les modales." % codes)
        return resultat

    for code, (mini, maxi) in BORNES.items():
        n = codes.count(code)
        if n < mini:
            resultat["raison"] = "Il faut au moins %d %s" % (mini, NOMS[code])
            return resultat
        if n > maxi:
            resultat["raison"] = "%d %ss : le maximum est %d" % (n, NOMS[code], maxi)
            return resultat

    if exiger_statut:
        if not statut:
            resultat["raison"] = "Statut manquant après la chaîne (%s)" % " / ".join(STATUTS)
            return resultat
        if statut not in STATUTS:
            resultat["raison"] = "Statut inconnu « %s » (%s)" % (statut, " / ".join(STATUTS))
            return resultat
    resultat["statut"] = statut

    resultat["transcription"] = transcrire(glyphes)
    resultat["ok"] = True
    return resultat


def transcrire(glyphes):
    """Mots-codes séparés par des points. Pas de crochets : une modale qualifie
    toujours la séance entière, jamais un glyphe en particulier."""
    return ".".join(mot(g) for g in glyphes)
