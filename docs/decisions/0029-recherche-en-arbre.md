# 0029 · Recherche en arbre

- **Statut** : appliquée (E13), **avec une justification corrigée par la mesure**
- **Écrite** : 2026-09-19
- **Mesurée** : 2026-09-19 — voir « Ce que la mesure a dit »

## Problème

La recherche rend des passages indépendants, classés par pertinence : quarante fragments
sans rapport entre eux. Deux conséquences. On ne voit pas **les relations** entre les
notes trouvées, alors que c'est souvent la réponse. Et pour faire répondre l'IA, on lui
envoie beaucoup de texte redondant.

## Décision

Une recherche qui part d'un point d'entrée et **se propage par les liens et les
backlinks**, en décroissant avec la distance.

- **Amorce** : les meilleurs résultats de la recherche hybride, ou la note ouverte.
- **Propagation** : liens sortants et entrants, sur une profondeur bornée.
- **Décroissance** : un nœud lointain pèse moins qu'un nœud proche, et la pertinence
  propre au nœud compte autant que sa position.
- **Plafond par niveau** : une note-carrefour à cinquante liens ne doit pas manger le
  budget à elle seule.
- **Dédoublonnage** : une note atteinte par deux chemins ne compte qu'une fois.
- **Budget** en caractères, rempli par ordre de priorité, et affiché.

### L'arbre s'affiche avant que l'IA parle

L'arbre est montré d'abord. Chaque nœud dit **pourquoi il est là** — pertinence propre,
lien depuis X, backlink depuis Y — et ce qu'il coûte. L'auteur décoche les branches
inutiles, puis lance la réponse.

C'est la règle de 0017 appliquée au contexte : l'IA propose ce qu'elle veut lire, l'auteur
valide. Et c'est ce qui répond à la seconde moitié du besoin — **voir les relations**, pas
seulement économiser des jetons.

## Sur l'économie de jetons

L'intuition de départ était que l'arbre ferait économiser des jetons. La décision exigeait
de le **mesurer, pas de le supposer**. C'est fait, et la mesure dit l'inverse.

## Ce que la mesure a dit

Banc reproductible : `tests/test_e13_arbre.py`, classe `Mesure`. 48 notes réparties en six
grappes, denses à l'intérieur, rarement reliées d'une grappe à l'autre — la forme d'un
vault réel. Tirage seedé, donc rejouable. Question : « prévision probabilité mesure ».

| | notes | caractères |
|---|---|---|
| recherche plate, non bornée | 40 | 48 557 |
| arbre (budget 40 000) | 29 | 37 911 |
| plate **tronquée au même budget** | 33 | 39 972 |

**L'arbre ne fait pas économiser de jetons.** Les 10 646 caractères qu'il semble
économiser face à la recherche plate non bornée sont l'effet du **plafond de budget**, et
n'importe quel plafond ferait autant. Comparé à la même recherche plate tronquée au même
budget, l'écart tombe à 2 061 caractères — 5 %, dans un sens ou dans l'autre selon la
forme du vault. Un second banc, avec des notes deux fois plus longues, donnait l'écart
inverse : l'arbre y coûtait 2 070 caractères de **plus**. Conclusion : à budget égal, c'est
le même prix.

Ce qui change, c'est **quelles** notes on paie :

- **12 des 29 notes retenues** n'étaient remontées par aucune recherche lexicale ou
  sémantique : elles ne sont là que parce qu'un lien y menait ;
- **21 des 29** viennent d'un lien (niveau > 0) et non d'un score propre ;
- la **carte** — 1 158 caractères — permet de répondre sur la relation entre deux notes,
  ce que quarante extraits indépendants ne permettent pas.

Deux cas où l'arbre ne sert à rien, relevés au passage :

- **vault minuscule** (6 notes) : la recherche plate rendait deux notes, très en dessous
  du budget. L'arbre coûte plus cher et n'apporte rien. Il n'a d'effet que lorsque la
  recherche plate déborde.
- **amorces formant une clique** : si les huit amorces se citent entre elles et rien
  d'autre, la propagation ne sort pas de l'ensemble de départ et l'arbre se réduit aux
  amorces. Vu sur un premier banc mal construit — l'arbre paraissait très économe parce
  qu'il ne trouvait rien. Le banc a été refait ; le piège est noté pour la prochaine fois.

**Conséquence sur la justification de l'étape** : « économiser des jetons » était la
mauvaise raison. La bonne est le **rappel par les liens** — retrouver ce que le score ne
retrouve pas — et la **lisibilité des relations**. Le plafond de budget, lui, mérite
d'exister partout où l'on alimente un modèle, pas seulement ici.

## Écarté

- **Alimenter l'IA directement** sans montrer l'arbre : plus rapide, mais on perd la
  moitié de l'intérêt.
- **Deux chemins réglables** : deux comportements à maintenir pour un gain incertain.
