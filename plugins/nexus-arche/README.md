# NEXUS-ARCHÊ

Lecture structurelle d'une situation complexe par seize cartes invariantes, en double
registre : mathématique (systèmes dynamiques, topologie, théorie des graphes) et
anthropologique (universaux comportementaux documentés par Donald Brown).

Décision de conception : [`docs/decisions/0039`](../../docs/decisions/0039-nexus-arche-en-plugin.md).
Source des cartes : [NEXUS-ARCHE](https://github.com/Othman-Benbrahim/NEXUS-ARCHE),
`references/cards.md`.

## Ce que cet outil n'est pas

Il **ne prédit pas, ne prescrit pas, ne diagnostique pas** — ni médicalement, ni
psychologiquement, ni juridiquement. C'est un dispositif de discipline, pas un oracle.

- « Une carte sans ancrage est une carte inactive — elle ne disparaît pas, elle attend
  une situation qui lui corresponde. »
- « Un tirage aléatoire est une génération assistée, pas un hasard sacré. »
- « La coïncidence lexicale n'est pas un ancrage » : un « réseau » nommé ne prouve pas
  RÉSEAU.

## État : lots 1 et 2

**Hors ligne, sans modèle :**

- **Catalogue** — les 16 cartes explorables : glyphe, registres rationnel et symbolique,
  branche mathématique, Question IRIS, et les critères « À ne pas confondre avec ».
  Filtre insensible aux accents.
- **Valideur de signature MÉMOIRE-Σ** — alphabet des 20 primitives, ordre des strates,
  comptes, statut, transcription en mots-codes.
- **Tirage** — 1, 2 ou 3 cartes par hasard cryptographique, avec les positions
  *tient / bouge / manque* pour la constellation.

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

À venir : configurations pathologiques du Mode 3, registre et calibration des erreurs de
distinction, fiche Markdown dans le vault.

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
| `/api/plugins/nexus-arche/lire` | POST | `{situation, imposees?}` → `{retenues, ecartees, distinctions}` |

Aucun secret, aucune permission réseau. Seule `/lire` consulte le modèle configuré dans
PRISME — votre clé, votre fournisseur. Permission : `vault_write` seulement, pour les
fiches à venir.

**Sans modèle configuré**, le catalogue, le valideur et le tirage restent utilisables :
l'ancrage est alors à votre charge, ce qui était de toute façon la forme d'origine du
protocole.

## Limites connues

- Rien n'est encore écrit dans le vault : aucune fiche n'est produite, aucune lecture
  n'est conservée.
- Les **configurations pathologiques 3 et 4** du Mode 3 ne sont pas détectées : elles
  supposent une relation d'*antagonisme* entre cartes que `references/calibration.md` ne
  documente pas — il n'y décrit que des *confusions*, ce qui est une autre relation.
- L'ancrage littéral empêche la fabrication, pas le mauvais choix : le modèle reste libre
  de citer un passage hors sujet. Le tirage aléatoire et votre propre jugement à la
  validation restent les garde-fous principaux.
- La calibration mesurera les **erreurs de distinction** — si l'auteur a choisi la carte
  qu'il jugera plus tard la bonne. Ce n'est pas la même chose que la calibration du
  plugin `calibration`, qui confronte une probabilité à un résultat observé. Les deux
  mots désignent des mesures différentes.
