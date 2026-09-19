# 0029 · Recherche en arbre

- **Statut** : acceptée, à appliquer (E13)
- **Écrite** : 2026-09-19

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

Le gain n'est pas d'envoyer moins de texte au hasard, c'est de pouvoir envoyer **une
carte** — titres et relations — accompagnée de quelques notes entières, au lieu de
quarante extraits qui se répètent. Le dédoublonnage et l'arrêt sur budget avec un ordre
justifié font le reste.

À mesurer, pas à supposer : l'étape devra comparer, sur les mêmes questions, les jetons
consommés et la qualité des réponses, entre la recherche plate et la recherche en arbre.

## Écarté

- **Alimenter l'IA directement** sans montrer l'arbre : plus rapide, mais on perd la
  moitié de l'intérêt.
- **Deux chemins réglables** : deux comportements à maintenir pour un gain incertain.
