# 0026 · Activation de l'horloge du monde

- **Statut** : acceptée, non encore appliquée
- **Écrite** : 2026-09-19

Précise [0022](0022-horloges-des-objets.md).

## Décision

L'horloge du monde (`prisme_valide_du`, `prisme_valide_au`, avec leurs champs d'état
`date | inconnue | ouverte`) **s'active en même temps que le plugin de calibration**
([0025](0025-calibration-en-plugin.md)), pas avant.

Jusque-là elle reste réservée et inactive, comme décidé en 0022 : un objet Source n'a que
sa date de publication, et une date de validité dans le monde n'aurait rien à mesurer.

## Pourquoi ça ne coûte rien d'attendre

Les champs sont **déjà réservés dans le frontmatter depuis E3**, avec leur distinction
« date inconnue » / « toujours vrai ». Les activer ne demandera aucune migration du
vault : c'était exactement le but de la réservation anticipée décidée en 0022.
