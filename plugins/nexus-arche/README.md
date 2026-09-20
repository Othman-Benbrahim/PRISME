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

## État : lot 1

Ce qui fonctionne aujourd'hui, entièrement hors ligne et sans modèle :

- **Catalogue** — les 16 cartes explorables : glyphe, registres rationnel et symbolique,
  branche mathématique, Question IRIS, et les critères « À ne pas confondre avec ».
  Filtre insensible aux accents.
- **Valideur de signature MÉMOIRE-Σ** — grammaire vérifiée : alphabet des 20 primitives,
  ordre des strates, comptes, statut, transcription en mots-codes.

À venir : lecture assistée par modèle avec ancrage littéral obligatoire, détection des
configurations pathologiques, registre et calibration des erreurs de distinction, fiche
Markdown dans le vault.

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

Aucun réseau, aucun secret. Permission : `vault_write` seulement, pour les fiches à venir.

## Limites connues

- Le lot 1 ne produit aucune fiche : il n'écrit rien dans le vault.
- La calibration mesurera les **erreurs de distinction** — si l'auteur a choisi la carte
  qu'il jugera plus tard la bonne. Ce n'est pas la même chose que la calibration du
  plugin `calibration`, qui confronte une probabilité à un résultat observé. Les deux
  mots désignent des mesures différentes.
