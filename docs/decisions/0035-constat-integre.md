# 0035 · Constat dans PRISME, sans extension requise

- **Statut** : demandé par l’auteur, implémenté et en revue
- **Écrite** : 2026-09-19

## Problème

La première livraison a suivi la décision 0031 en ajoutant un bouton à l’extension
Firefox. L’auteur a précisé qu’il souhaitait intégrer Constat directement à PRISME,
en reprenant la structure de l’add-on. Cette précision remplace le choix d’interface
de 0031 et du handoff précédent.

## Décision

Constat devient un plugin PRISME avec son espace de dossiers et son pipeline.
Les fonctions méthodologiques de l’extension sont reprises dans des modules JS ;
la persistance et les appels au modèle passent par PRISME. Aucun add-on ni clé
d’agent n’est nécessaire. Le versement devient une proposition interne de la
session de l’auteur ; la file attend toujours une acceptation explicite.

La chaîne garde trois pièces séparées : E11 pour le type Prédiction, Calibration
pour les calculs et l’horloge du monde (0025/0026), Constat pour l’instruction des
hypothèses. E11 ne contient PAS les calculs de calibration. E9 attend les précisions
de l’auteur. La précédente livraison de l’extension est remplacée pour ce parcours.

## Écarté

- Faire dépendre l’usage de Constat dans PRISME d’une extension ou d’une clé d’agent.
- Réécrire l’analyse sous une forme simplifiée qui perdrait l’ACH, les rejets et les validations.
- Mélanger scores de calibration et classement ACH.
- Présenter les notes/exports anciens sans textes comme un corpus restauré complet.
