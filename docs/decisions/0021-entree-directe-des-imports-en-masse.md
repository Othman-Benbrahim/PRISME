# 0021 · Entrée directe des imports en masse

- **Statut** : acceptée, non encore appliquée (E5)
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
