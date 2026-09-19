"""Propagation par les liens : construction de l'arbre (docs/decisions/0029).

La recherche ordinaire rend des passages indépendants. Ici on part d'une amorce et on
se propage par les `[[liens]]` et les backlinks, en décroissant avec la distance.

**Ce que ça apporte, mesuré** (décision 0029, section « Ce que la mesure a dit », banc
rejouable dans `tests/test_e13_arbre.py`) : pas une économie de jetons. À budget égal,
l'arbre coûte le même prix que la recherche plate tronquée, à 5 % près. Ce qu'il apporte,
c'est le **rappel par les liens** — 12 notes retenues sur 29 n'étaient remontées par aucun
score — et la carte des relations. L'économie, elle, vient du seul `BUDGET`, qui vaudrait
partout où l'on alimente un modèle, pas ici seulement.

Quatre garde-fous, tous nécessaires :

- **plafond par parent et par niveau** — une note-carrefour à cinquante liens mangerait
  le budget à elle seule ;
- **décroissance** — un nœud à deux pas pèse moins qu'un nœud à un pas ;
- **dédoublonnage** — une note atteinte par deux chemins ne compte qu'une fois, et garde
  le meilleur des deux scores ;
- **budget** en caractères, rempli par ordre de priorité.

Ce qui dépasse le budget reste dans l'arbre, marqué non retenu : on doit voir ce qui a
été écarté, pas seulement ce qui a été gardé.
"""
from pathlib import Path

PROFONDEUR = 2
AMORCES = 8
PAR_PARENT = 6
PAR_NIVEAU = 18
DECROISSANCE = 0.45          # un nœud vaut moins de la moitié de son parent
BUDGET = 40_000              # caractères ; un contexte plus gros ne se relit plus
MAX_PAR_NOTE = 6_000         # une note très longue est tronquée, pas écartée


class Noeud:
    __slots__ = ("chemin", "nom", "niveau", "parent", "motif", "pertinence", "score",
                 "taille", "retenu", "enfants")

    def __init__(self, chemin, nom, niveau, parent, motif, pertinence, score, taille):
        self.chemin = chemin
        self.nom = nom
        self.niveau = niveau
        self.parent = parent
        self.motif = motif
        self.pertinence = pertinence
        self.score = score
        self.taille = taille
        self.retenu = False
        self.enfants = []

    def en_dict(self):
        return {"chemin": self.chemin, "nom": self.nom, "niveau": self.niveau,
                "parent": self.parent, "motif": self.motif,
                "pertinence": round(self.pertinence, 4), "score": round(self.score, 4),
                "taille": self.taille, "retenu": self.retenu,
                "enfants": [e.chemin for e in self.enfants]}


def _taille(chemin):
    try:
        return Path(chemin).stat().st_size
    except OSError:
        return 0


def _liens_sortants(index, chemin):
    with index.read() as conn:
        rows = conn.execute(
            "SELECT DISTINCT l.target_path AS cible, c.name AS nom FROM links l "
            "JOIN files f ON f.id = l.file_id "
            "LEFT JOIN files c ON c.path = l.target_path "
            "WHERE f.path = ? AND l.target_path IS NOT NULL AND l.target_path != f.path",
            (chemin,)).fetchall()
    return [(r["cible"], r["nom"] or Path(r["cible"]).name) for r in rows]


def _liens_entrants(index, chemin):
    from ..index import search as lexical
    return [(b["path"], b["name"]) for b in lexical.backlinks(index, chemin)]


def construire(index, question, depart=None, profondeur=PROFONDEUR, budget=BUDGET,
               racine=None, cfg=None):
    """Renvoie l'arbre : amorces, propagation, scores, budget appliqué.

    `depart` amorce sur une note précise ; sans lui, l'amorce est la recherche hybride.
    """
    from ..vecteurs.recherche import hybride

    pertinences, info = {}, {"mode": "lexical", "semantique": False, "repli": ""}
    if question:
        resultats, info = hybride(index, question, limit_files=40, racine=racine, cfg=cfg)
        for rang, r in enumerate(resultats, start=1):
            pertinences[r["path"]] = 1.0 / (1 + rang)

        # ── Repli par terme ────────────────────────────────────────────
        # La recherche lexicale exige **tous** les termes. Sur un vault où
        # « calibration » est dans une note et « Brier » dans une autre, la question
        # « calibration Brier » ne rend rien : l'arbre sort vide alors que ses deux
        # amorces existent, à un lien l'une de l'autre. C'est exactement le cas que
        # l'arbre devrait servir le mieux.
        #
        # On ne touche pas à la recherche générale — ce serait changer le sens de
        # `/api/search` pour tout le monde. Ici seulement, et seulement quand la
        # question à plusieurs termes ne rend rien, on reprend terme par terme et on
        # réunit. Les amorces ainsi trouvées pèsent moins : elles satisfont une partie
        # de la question, pas la question.
        mots = [m for m in question.split() if len(m) >= 2]
        if not pertinences and len(mots) > 1:
            for mot in mots[:6]:
                partiels, _i = hybride(index, mot, limit_files=12, racine=racine, cfg=cfg)
                for rang, r in enumerate(partiels, start=1):
                    valeur = 0.5 / (1 + rang)
                    if valeur > pertinences.get(r["path"], 0.0):
                        pertinences[r["path"]] = valeur
            if pertinences:
                info = dict(info, repli_par_terme=True)

    noeuds, ordre = {}, []

    def ajouter(chemin, nom, niveau, parent, motif, score):
        existant = noeuds.get(chemin)
        if existant is not None:
            # Atteint par deux chemins : le score monte, mais **le parent ne change
            # jamais**. La propagation est en largeur, donc le premier parent est celui
            # du plus court chemin ; le réattribuer produirait des cycles — une amorce
            # se retrouvait fille de sa propre descendante.
            if score > existant.score:
                existant.score = score
            return None
        n = Noeud(chemin, nom, niveau, parent, motif, pertinences.get(chemin, 0.0),
                  score, _taille(chemin))
        noeuds[chemin] = n
        ordre.append(n)
        return n

    # ── Amorce ───────────────────────────────────────────────────────────
    if depart:
        ajouter(str(depart), Path(depart).name, 0, "", "note ouverte", 1.0)
    for rang, (chemin, pert) in enumerate(sorted(pertinences.items(), key=lambda kv: -kv[1])):
        if rang >= AMORCES:
            break
        ajouter(chemin, Path(chemin).name, 0, "", "pertinence", pert)

    # ── Propagation ──────────────────────────────────────────────────────
    niveau_courant = [n for n in ordre if n.niveau == 0]
    for niveau in range(1, profondeur + 1):
        suivant, places = [], PAR_NIVEAU
        for parent in sorted(niveau_courant, key=lambda n: -n.score):
            if places <= 0:
                break
            voisins = ([(c, nm, "lien") for c, nm in _liens_sortants(index, parent.chemin)]
                       + [(c, nm, "backlink") for c, nm in _liens_entrants(index, parent.chemin)])
            pris = 0
            for chemin, nom, genre in voisins:
                if pris >= PAR_PARENT or places <= 0:
                    break
                herite = parent.score * DECROISSANCE
                score = pertinences.get(chemin, 0.0) + herite
                motif = "%s %s %s" % ("lien depuis" if genre == "lien" else "backlink depuis",
                                      "←" if genre == "backlink" else "→", parent.nom)
                n = ajouter(chemin, nom, niveau, parent.chemin, motif, score)
                if n is not None:
                    parent.enfants.append(n)
                    suivant.append(n)
                    pris += 1
                    places -= 1
        niveau_courant = suivant
        if not suivant:
            break

    # ── Budget ───────────────────────────────────────────────────────────
    classes = sorted(ordre, key=lambda n: (-n.score, n.chemin))
    consomme = 0
    for n in classes:
        cout = min(n.taille, MAX_PAR_NOTE)
        if consomme + cout > budget:
            continue                      # trop gros pour ce qui reste : on passe au suivant
        n.retenu = True
        consomme += cout

    return {
        "question": question or "",
        "depart": str(depart or ""),
        "noeuds": [n.en_dict() for n in classes],
        "retenus": [n.chemin for n in classes if n.retenu],
        "budget": budget,
        "consomme": consomme,
        "profondeur": profondeur,
        "recherche": info,
        "comptes": {
            "total": len(ordre),
            "amorces": sum(1 for n in ordre if n.niveau == 0),
            "par_lien": sum(1 for n in ordre if n.niveau > 0),
            "retenus": sum(1 for n in ordre if n.retenu),
            "ecartes": sum(1 for n in ordre if not n.retenu),
        },
    }
