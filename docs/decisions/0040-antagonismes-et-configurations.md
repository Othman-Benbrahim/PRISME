# 0040 · Antagonismes structurels — une relation manquante, produite en amont

- **Statut** : acceptée, appliquée (lot 3 du plugin NEXUS-ARCHÊ)
- **Écrite** : 2026-09-21
- **Prolonge** : [0039](0039-nexus-arche-en-plugin.md)

## Problème

`references/protocol.md` du dépôt NEXUS-ARCHÊ décrit quatre **configurations
pathologiques** du Mode 3. Deux d'entre elles reposent sur une relation qui n'existe
nulle part dans le corpus :

> **Configuration 3 — Lacune active contradictoire** : la structure absente est
> structurellement **incompatible** avec la structure stable.
>
> **Configuration 4 — Tension maximale** : les 3 cartes appartiennent à des **registres
> antagonistes**.

`references/calibration.md` documente des *confusions* — la probabilité qu'un lecteur
prenne une carte pour une autre. Ce n'est pas la même relation : HIÉRARCHIE et RÉSEAU
sont parmi les plus confondues, et une hiérarchie *est* un graphe, donc les deux cartes
peuvent parfaitement décrire le même objet.

Trois issues se présentaient : renoncer aux configurations 3 et 4 ; les câbler sur la
matrice de confusion, qui répond à une autre question ; ou produire la relation absente.

## Décision

**Produire la relation dans le dépôt NEXUS-ARCHÊ, pas dans le plugin.**

Le plugin est une copie des références. Inventer une table dans son code aurait créé un
NEXUS-ARCHÊ divergent : deux corpus, dont l'un n'existe que pour PRISME et ne bénéficie
à aucun autre usage du dispositif. La table est donc écrite en amont, dans
`references/antagonismes.md` (v0.3.1), et portée ici comme `cartes.json` l'a été.

### Le critère d'inscription

Une paire entre dans la table si, et seulement si, les **registres rationnels** des deux
cartes portent des prédicats qui ne peuvent pas être vrais du même objet. Chaque ligne
cite le texte de `cards.md` qui la fonde. Neuf paires sur 120.

**Aucun antagonisme n'est dérivé du « ou » d'un critère discriminant.** Ce « ou » —
« s'agit-il de X *ou* de Y ? » — dit quelle carte retenir pour une lecture, pas que les
structures s'excluent dans le monde. Appliqué mécaniquement, il aurait fait de
HIÉRARCHIE et RÉSEAU des antagonistes.

### Un antagonisme n'est pas une contradiction

Deux structures incompatibles portant sur **deux objets distincts** ne se contredisent
pas : une équipe peut connaître une CROISSANCE d'effectif pendant qu'une ÉMERGENCE se
produit dans ses pratiques.

Le code ne peut pas trancher cela — il ne voit pas la situation. Il produit donc un
**signal** accompagné de la question qui le tranche, posée à l'auteur : *ces deux
structures portent-elles sur la même chose ?* C'est le partage de 0039 appliqué à une
autre matière : le code vérifie le vérifiable, l'auteur juge ce qui demande de connaître
la situation.

### La configuration 4 se déclenche à deux paires, pas trois

La table ne contient aucun triangle : aucune constellation n'a ses trois paires
antagonistes. Exiger les trois rendrait la configuration inatteignable **par
construction** — elle serait documentée et jamais déclenchée, ce qui est pire que
l'absence. Avec deux paires : dix constellations sur 560, soit 1,8 %. Le protocole
annonçait « signal rare mais fort ».

### Une carte inactive n'entre dans aucune configuration

Une carte tirée sans ancrage littéral est déclarée inactive. Sa position reste vide, et
aucune configuration ne peut être prononcée dessus. Sans cette règle, une constellation
dont deux cartes n'ont pas tenu produirait quand même un diagnostic.

## Écarté

- **Une partition des 16 cartes en « registres »**, malgré la lettre du protocole. Elle
  n'existe nulle part : il aurait fallu l'inventer, et une taxonomie de notre cru aurait
  servi de fondement à un diagnostic. L'antagonisme est défini paire à paire, depuis des
  définitions déjà écrites.
- **Câbler les configurations sur la matrice de confusion.** Elle répond à « qui risque
  de confondre quoi », pas à « qu'est-ce qui s'exclut ». Cinq des dix-sept paires de la
  matrice sont antagonistes ; les douze autres ne le sont pas.
- **Renoncer aux configurations 3 et 4.** C'était la position du lot 2, faute de table.
  Elle laissait deux tiers du Mode 3 non implémentés et un protocole partiellement mort.
- **Faire produire la relation par le modèle.** Une incompatibilité entre deux
  définitions est une propriété du catalogue, pas de la situation : elle se calcule une
  fois pour toutes et se vérifie. La faire rédiger à chaque lecture rendrait variable ce
  qui est fixe.

## Révision à prévoir

La configuration 2 (« ce qui bouge est de même nature que ce qui tient ») est définie
par un **voisinage documenté** : la paire figure dans les rubriques « À ne pas confondre
avec » et n'est pas antagoniste. C'est une relation écrite pour un autre usage, réemployée
faute d'axe de *nature* dans le corpus. Seize paires sur 120, 13 % des constellations —
plus fréquent qu'une pathologie ne devrait l'être. Signalée comme la définition la plus
fragile, dans les références comme dans le code, et à réviser sur données réelles.
