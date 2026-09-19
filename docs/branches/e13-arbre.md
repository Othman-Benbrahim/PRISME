# E13 — Recherche en arbre

## Objectif

Chercher en suivant les `[[liens]]` et les backlinks au lieu de rendre quarante passages
indépendants, montrer l'arbre obtenu, laisser l'auteur élaguer, et seulement ensuite faire
répondre l'IA. Décision appliquée :
[0029](../decisions/0029-recherche-en-arbre.md).

## La justification de l'étape a changé en cours de route

L'intuition de départ — la mienne comme celle de la demande — était que l'arbre ferait
**économiser des jetons**. La décision 0029 exigeait de le mesurer plutôt que de le
supposer. La mesure a été faite, et elle dit l'inverse.

Banc rejouable : `tests/test_e13_arbre.py`, classe `Mesure`. 48 notes en six grappes,
denses à l'intérieur, rarement reliées entre elles — la forme d'un vault réel. Tirage
seedé.

| | notes | caractères |
|---|---|---|
| recherche plate, non bornée | 40 | 48 557 |
| arbre (budget 40 000) | 29 | 37 911 |
| plate **tronquée au même budget** | 33 | 39 972 |

Les 10 646 caractères que l'arbre semble économiser face à la recherche plate non bornée
sont l'effet du **plafond de budget**, pas de l'arbre : n'importe quel plafond ferait
autant. Comparé à la même recherche plate tronquée au même budget, l'écart tombe à 5 %,
dans un sens ou dans l'autre selon la forme du vault — un second banc, avec des notes deux
fois plus longues, donnait l'arbre plus cher de 2 070 caractères. **À budget égal, c'est
le même prix.**

Ce qui change, c'est **quelles** notes on paie :

- **12 des 29 notes retenues** n'étaient remontées par aucune recherche, ni lexicale ni
  sémantique : elles ne sont là que parce qu'un lien y menait ;
- **21 des 29** viennent d'un lien et non d'un score propre ;
- la **carte** des relations — 1 158 caractères — permet de répondre sur le rapport entre
  deux notes, ce que quarante extraits indépendants ne permettent pas.

Donc : l'étape se justifie par le **rappel par les liens** et la lisibilité des relations,
pas par l'économie. Le plafond de budget, lui, mérite d'exister partout où l'on alimente
un modèle, pas seulement ici.

Deux cas où l'arbre ne sert à rien, relevés aussi :

- **vault minuscule** — la recherche plate rendait deux notes, très sous le budget :
  l'arbre coûte plus cher et n'apporte rien. Il n'a d'effet que si la plate déborde ;
- **amorces formant une clique** — si les huit amorces se citent entre elles et rien
  d'autre, la propagation ne sort pas du point de départ. Vu sur un premier banc mal
  construit, où l'arbre paraissait très économe parce qu'il ne trouvait rien.

## Ce qui change

### La propagation

On part des meilleurs résultats de la recherche hybride (E7) ou de la note ouverte, et on
suit les liens sortants et entrants sur une profondeur bornée. Quatre garde-fous, tous
nécessaires :

- **décroissance** (0,45) — un nœud à deux pas pèse moins qu'un nœud à un pas, et sa
  pertinence propre s'ajoute à ce qu'il hérite ;
- **plafond par parent (6) et par niveau (18)** — une note-carrefour à cinquante liens
  mangerait le budget à elle seule ;
- **dédoublonnage** — une note atteinte par deux chemins ne compte qu'une fois ;
- **budget** en caractères (40 000 par défaut), rempli par ordre de score.

Ce qui dépasse le budget **reste dans l'arbre**, marqué non retenu. On doit voir ce qui a
été écarté, sinon l'élagage se fait sur un arbre déjà tronqué en secret.

### Le parent ne bouge jamais

Une note atteinte une seconde fois voit son score monter, mais **garde le parent du
premier passage**. La propagation est en largeur, donc ce premier parent est celui du plus
court chemin.

Réattribuer le parent produit des cycles, et ça s'est produit : `Methode`, amorce de niveau
0, se retrouvait fille de `Calibration`, qui est sa propre descendante. L'arbre affiché
bouclait. `test_aucun_cycle` remonte tous les parents de chaque nœud et refuse une boucle.

### L'arbre se voit et s'élague avant que l'IA parle

`/api/arbre/construire` **n'appelle pas le modèle**. C'est le point de la décision : chaque
nœud dit pourquoi il est là — pertinence, lien depuis X, backlink depuis Y — et ce qu'il
coûte. L'auteur décoche, le compteur et la jauge bougent, puis `/api/arbre/repondre`
envoie la carte et les seules notes cochées.

C'est la règle de [0017](../decisions/0017-provenance-editable.md) appliquée au contexte :
l'IA propose ce qu'elle veut lire, l'auteur valide.

### Les « retenus » sont filtrés côté serveur

La liste des notes cochées revient du navigateur et sert à **lire des fichiers**. Un chemin
qui ne figure pas dans l'arbre construit n'est jamais lu, même s'il est dans le vault :
sans ce filtre, la route deviendrait un lecteur de fichiers arbitraire. `safe_path`
protégerait encore, mais en silence ; ici on refuse explicitement.

## Routes

| Route | Rôle |
|---|---|
| `POST /api/arbre/construire` | Amorce, propage, applique le budget. **N'appelle pas le modèle.** `comparer: true` ajoute la mesure |
| `POST /api/arbre/repondre` | Assemble la carte + les notes cochées, et interroge le modèle |

Profondeur plafonnée à 4, budget à 200 000 caractères.

## Interface

Un bouton `🌳 Arbre` dans la barre, et une passerelle « Poursuivre en arbre » depuis la
fenêtre de recherche — la recherche plate est le point de départ naturel.

La fenêtre montre la liste des nœuds : niveau, nom cliquable, motif de présence, coût.
Un bandeau de budget avec jauge, « Tout » / « Rien ». Le bouton de réponse reste désactivé
tant que rien n'est coché. La mesure face à la recherche plate s'affiche telle quelle,
y compris quand elle dessert l'arbre.

## Un bug attrapé au navigateur

`core.css` met `width:100%` sur les `input` — c'est fait pour les champs des fenêtres. La
case à cocher de chaque ligne occupait donc les 794 px de la ligne et poussait le nom, le
motif et le coût hors du cadre : la liste n'affichait plus que des cases flottantes. Le
DOM était correct, les styles calculés corrects, les tests verts. Seule la capture d'écran
l'a montré. Corrigé par une largeur explicite ; `test_la_case_a_cocher_garde_sa_largeur`
garde la trace.

## Fichiers

| Fichier | Rôle |
|---|---|
| `prisme_core/arbre/parcours.py` | Amorce, propagation, scores, budget |
| `prisme_core/arbre/contexte.py` | Carte des relations, assemblage, `comparer()`, consigne |
| `prisme_core/routes/arbre.py` | Les deux routes, et le filtre des « retenus » |
| `prisme_core/web/js/arbre.js` | Construction, élagage, compteur de budget, réponse |
| `prisme_core/web/css/arbre.css` | Mise en forme de la liste et du bandeau |
| `prisme_core/web/index.html` | Bouton, fenêtre, passerelle depuis la recherche |
| `tests/test_e13_arbre.py` | 32 tests |

## Vérifié

- 320 tests, dont 32 pour cette étape : forme de l'arbre (absence de cycle, plafonds,
  budget), garde du vault (départ hors vault, « retenus » forgés), et la mesure elle-même
  — figée dans les tests pour que personne ne la réécrive à la baisse sans s'en apercevoir.
- Dans le navigateur : construction, motifs lisibles, décochage qui fait bouger le compteur
  et la jauge, bouton de réponse désactivé quand plus rien n'est coché, erreur du service
  IA affichée proprement, passerelle depuis la recherche.
