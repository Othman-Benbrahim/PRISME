# 0021 · Entrée directe des imports en masse

- **Statut** : appliquée en E5, pour le type Source
- **Écrite** : 2026-09-17

Inspirée d'Utopia (fiche 0015). Amende [0017](0017-objets-conceptuels.md).

## Problème

Si chaque objet extrait d'un import en masse attend une validation, la file devient ingérable et finit abandonnée.

## Décision

- Un objet issu d'un **import en masse** entre directement dans le vault quand sa confiance est élevée. Il porte `prisme_statut: non_relu`.
- **La confiance repose sur des signaux vérifiables, pas sur l'auto-évaluation du modèle.** Pour le type Source : un identifiant repéré mécaniquement (URL valide, DOI, identifiant arXiv, ISBN) donne une confiance élevée ; une référence seulement déduite par l'IA part en file. Chaque futur type définit ses signaux ; sans signal vérifiable, l'objet part en file.
- **Passent toujours par la file**, même avec une confiance élevée : les propositions des agents ([0018](0018-acces-des-agents.md)), les « retiens ceci », les doublons possibles et les contradictions avec un objet existant.
- **Réversibilité.** Une vue liste les objets non relus. Retirer un objet non relu l'envoie à la corbeille et mémorise le rejet (avec sa raison si elle est donnée). Chaque import porte un identifiant de lot ; « annuler ce lot » retire d'un coup ses objets **encore non relus**, jamais ceux qui ont été relus.
- Une note qui cite un objet non relu l'affiche avec un marqueur.
- Le seuil et l'entrée directe elle-même se règlent par type d'objet.

## Écarté

- Tout faire passer par la file (0017 dans sa version initiale).

## Application en E5

Pour le type Source, le signal vérifiable est la **forme** de la référence : une URL
valide, un DOI, un identifiant arXiv ou un ISBN repérés par expression régulière entrent
directement, avec `prisme_relu: false` et un `prisme_lot`. Les mentions en clair que
seule l'IA reconnaît partent en file, et chacune doit citer un extrait littéral de la
note, vérifié avant affichage : une proposition dont l'extrait est introuvable est
écartée sans être montrée.

« Annuler ce lot » retire les objets non relus et conserve les autres. Retirer un objet
mémorise le rejet avec sa raison, que l'IA relit avant de proposer à nouveau. Une note
qui cite un objet non relu porte un marqueur ambre dans l'en-tête de l'éditeur.

Le seuil par type reste à faire : il n'a de sens qu'avec un deuxième type d'objet.

## Révision du 19 septembre 2026 — E11

Voir [0033](0033-types-objets.md) : cinq types et paramètres par type implémentés,
en revue. Aucun signal mécanique ne permet l’entrée directe des nouveaux types.
Le gel et leur fusion réversible restent reportés ; la fusion Source reste disponible.
