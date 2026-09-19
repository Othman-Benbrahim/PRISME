# 0034 · Copies de référence pour la calibration

- **Statut** : implémentée, en revue dans `plugin-calibration`
- **Écrite** : 2026-09-19

## Problème

Une note E11 est éditable. Calculer sur sa probabilité actuelle après observation
permettrait de réécrire le pari. La date de création seule ne prouve pas le contenu.

## Décision

Le plugin capture explicitement une référence locale avant le jour de l'échéance
(UTC), sur une prédiction ouverte et relue. Il conserve le pari, l'identifiant,
la date de copie et les bornes du monde E3 dans le vault. Le score utilise cette
référence et le résultat actuel accompagné de sa preuve. Une modification des
champs du pari entraîne une exclusion, expliquée dans le rapport.

Une empreinte détecte l'altération accidentelle ; il n'y a aucun tiers de confiance.
Le plugin refuse de remplacer une copie, mais le vault reste éditable hors PRISME.
La capture ne certifie ni l'ignorance du résultat ni un horodatage juridique.
L'horizon est mesuré à la capture, pas à la création d'une note qui a pu changer.

Les bornes du monde sont distinctes de l'échéance du pari ; inconnue et ouverte
restent distinctes. La copie conserve les bornes utilisées pour le filtre daté.
Les mesures, leurs agrégations et les exclusions vivent uniquement dans le plugin.

## Écarté

- Scorer rétrospectivement une ancienne fiche sans référence capturée.
- Écraser une copie lors d'une nouvelle inscription.
- Confondre cette protection locale avec un gel probant ou une reconstitution
  de toutes les connaissances à une date passée.
- Présenter un biais descriptif sur un faible effectif comme une preuve systématique.
