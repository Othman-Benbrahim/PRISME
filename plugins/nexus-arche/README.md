# NEXUS-ARCHÊ

Lecture structurelle d'une situation complexe par seize cartes invariantes, en double
registre : mathématique (systèmes dynamiques, topologie, théorie des graphes) et
anthropologique (universaux comportementaux documentés par Donald Brown).

Décisions de conception : [`0039`](../../docs/decisions/0039-nexus-arche-en-plugin.md) et
[`0040`](../../docs/decisions/0040-antagonismes-et-configurations.md).
Source des cartes et des antagonismes : [NEXUS-ARCHE](https://github.com/Othman-Benbrahim/NEXUS-ARCHE),
`references/cards.md` et `references/antagonismes.md` (v0.3.1).

## Ce que cet outil n'est pas

Il **ne prédit pas, ne prescrit pas, ne diagnostique pas** — ni médicalement, ni
psychologiquement, ni juridiquement. C'est un dispositif de discipline, pas un oracle.

- « Une carte sans ancrage est une carte inactive — elle ne disparaît pas, elle attend
  une situation qui lui corresponde. »
- « Un tirage aléatoire est une génération assistée, pas un hasard sacré. »
- « La coïncidence lexicale n'est pas un ancrage » : un « réseau » nommé ne prouve pas
  RÉSEAU.

## État : lots 1 à 3

**Hors ligne, sans modèle :**

- **Catalogue** — les 16 cartes explorables : glyphe, registres rationnel et symbolique,
  branche mathématique, Question IRIS, et les critères « À ne pas confondre avec ».
  Filtre insensible aux accents.
- **Valideur de signature MÉMOIRE-Σ** — alphabet des 20 primitives, ordre des strates,
  comptes, statut, transcription en mots-codes.
- **Tirage** — 1, 2 ou 3 cartes par hasard cryptographique, avec les positions
  *tient / bouge / manque* pour la constellation.
- **Configurations pathologiques du Mode 3** — les quatre, calculées sur la table des
  antagonismes. Aucun modèle n'intervient : c'est une question de catalogue.
- **Fiche dans le vault** — la lecture archivée en Markdown, au format de votre choix.

**Avec un modèle configuré :**

- **Lecture assistée** — vous décrivez la situation, le modèle propose 2 à 3 cartes,
  chacune avec un **ancrage** et une anti-résonance. Les questions de distinction entre
  les cartes retenues vous sont posées, à vous de trancher.

### L'ancrage doit être une citation

C'est ce qui empêche le dispositif de tourner à vide.

Le test d'ancrage veut qu'une carte sans observation concrète soit déclarée inactive.
Tant que vous fournissiez l'observation, ce test avait du mordant. Si le **même modèle**
propose la carte *et* rédige l'observation qui la justifie, on ne mesure plus que sa
fluidité : un modèle sait toujours étayer ce qu'il vient de choisir.

L'ancrage rendu doit donc être un **extrait littéral de votre texte**, vérifié par
comparaison de chaînes. Sans correspondance, la carte est écartée avant de vous être
montrée — mais elle reste affichée, avec le passage refusé et le motif, parce qu'une
carte inactive ne disparaît pas.

Les variations de forme sont tolérées — apostrophe courbe, espaces, accents perdus. Les
variations de contenu ne le sont pas : une paraphrase est refusée.

### Le tirage est le mode le plus rigoureux

Contre-intuitivement. C'est **le seul où le modèle ne choisit pas ce qu'il va
justifier** : les cartes sortent d'abord, il doit ensuite trouver un ancrage ou déclarer
la carte inactive.

### Un antagonisme n'est pas une contradiction

Les configurations 3 et 4 reposent sur une relation d'**antagonisme** entre cartes : deux
structures dont les définitions ne peuvent pas être vraies du même objet. Neuf paires sur
120, chacune fondée sur une citation des références.

Mais deux structures incompatibles portant sur deux objets distincts ne se contredisent
pas : une équipe peut connaître une CROISSANCE d'effectif pendant qu'une ÉMERGENCE se
produit dans ses pratiques. Le code ne voit pas la situation et ne peut pas trancher. Il
affiche donc un **signal** avec la question qui le tranche — *ces deux structures
portent-elles sur la même chose ?* — et vous laisse répondre.

Une carte déclarée inactive n'entre dans aucune configuration : sa position reste vide.

**La confusion n'est pas l'antagonisme.** HIÉRARCHIE et RÉSEAU sont parmi les cartes les
plus confondues, et une hiérarchie *est* un graphe : elles ne s'excluent pas. Les deux
relations sont tenues séparées, et le plugin le vérifie par un test.

### La fiche est vérifiée avant d'être écrite

Au moment d'archiver, les ancrages repassent le test littéral, les noms de cartes sont
relus depuis le catalogue, les configurations sont recalculées et la signature Σ validée.
Une fiche est ce qui survit à la séance : elle ne doit pas pouvoir contenir une citation
qui n'en est pas une, même si l'écran l'affichait.

Deux formats, au choix : la **fiche complète** garde la situation, les anti-résonances et
les questions restées ouvertes ; le **bloc condensé** garde les ancrages, les
configurations et les réserves. Aucun des deux ne se passe des réserves — une fiche
archivée sans elles finirait par se lire comme un verdict.

À venir : registre et calibration des erreurs de distinction.

## Les deux alphabets

Le catalogue NEXUS et MÉMOIRE-Σ partagent quinze glyphes **avec des sens différents** :

| Glyphe | Au catalogue NEXUS | En signature MÉMOIRE-Σ |
|---|---|---|
| `⊥` | SEUIL — bifurcation irréversible de la situation | LIMITE — piste close ou abandonnée |
| `∿` | TRANSFORMATION — mutation progressive | MOUVEMENT — travail en cours |
| `◊` | TRACE · MÉMOIRE — l'empreinte dans la situation | TRACE — session de reprise |

**La signature décrit la séance d'analyse, pas la situation analysée.** Le valideur
refuse tout glyphe du catalogue qui n'appartient pas à l'alphabet Σ — c'est le garde-fou
qui empêche les deux notations de se mélanger.

## Routes

| Route | Méthode | Rôle |
|---|---|---|
| `/api/plugins/nexus-arche/catalogue` | GET | Les 16 cartes |
| `/api/plugins/nexus-arche/distinctions?a=&b=` | GET | Les critères qui séparent deux cartes |
| `/api/plugins/nexus-arche/valider_signature` | POST | `{chaine}` → `{ok, raison, transcription, statut}` |
| `/api/plugins/nexus-arche/etat` | GET | Disponibilité du modèle, modes de tirage |
| `/api/plugins/nexus-arche/tirage` | POST | `{mode: 1\|2\|3}` → cartes tirées (CSPRNG) |
| `/api/plugins/nexus-arche/lire` | POST | `{situation, imposees?, positions?}` → `{retenues, ecartees, distinctions, configurations}` |
| `/api/plugins/nexus-arche/fiche` | POST | `{situation, retenues, format, statut?, signature?}` → note écrite dans le vault |

Aucun secret, aucune permission réseau. Seule `/lire` consulte le modèle configuré dans
PRISME — votre clé, votre fournisseur. Permission : `vault_write`, pour les fiches.

**Sans modèle configuré**, le catalogue, le valideur et le tirage restent utilisables :
l'ancrage est alors à votre charge, ce qui était de toute façon la forme d'origine du
protocole.

## Limites connues

- La **configuration 2** repose sur un « voisinage documenté » — la paire figure dans les
  rubriques « À ne pas confondre avec » et n'est pas antagoniste. C'est une relation
  écrite pour un autre usage, réemployée faute d'axe de *nature* dans le corpus. Seize
  paires sur 120, 13 % des constellations : plus fréquent qu'une pathologie ne devrait
  l'être. Signal indicatif, à réviser sur données réelles.
- L'ancrage littéral empêche la fabrication, pas le mauvais choix : le modèle reste libre
  de citer un passage hors sujet. Le tirage aléatoire et votre propre jugement à la
  validation restent les garde-fous principaux.
- La calibration mesurera les **erreurs de distinction** — si l'auteur a choisi la carte
  qu'il jugera plus tard la bonne. Ce n'est pas la même chose que la calibration du
  plugin `calibration`, qui confronte une probabilité à un résultat observé. Les deux
  mots désignent des mesures différentes.
