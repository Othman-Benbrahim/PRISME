# Plugin de calibration — après E11

## Objectif

Mesurer des paris conservés avant résolution, sans placer les calculs dans E11.
Le plugin active aussi l'horloge du monde prévue par 0026. Le bouton Constat est
une livraison distincte, dans son propre dépôt. E9 attend les précisions de l'auteur.

## Fichiers touchés

Créés : `plugins/calibration/` (calculs, copies, routes, interface, documentation),
`prisme_core/horloge.py`, `tests/test_calibration.py`, décision 0034 et cette fiche.
Modifiés : API publique des plugins, descriptions de provenance, liste attendue
des plugins livrés, feuille de route et suivi des décisions. Aucun fichier supprimé.
Aucune dépendance ajoutée. `vault.py` et `core.css` inchangés.

## Ruptures

Aucune migration. Les champs E3 de validité ne sont écrits que sur confirmation.
Une prédiction E11 reste utilisable sans le plugin. L'inscription dans la calibration
est volontaire et distincte de sa création. La copie constitue une référence locale,
pas un historique inviolable. Voir [0034](../decisions/0034-copies-calibration.md).

## Tester

```powershell
python -m unittest discover -s tests -p "test_calibration.py" -v
python -m unittest discover -s tests
```

Résultat Linux : **406 tests, 387 réussis, 19 ignorés**. Les 20 nouveaux tests portent
sur scores connus, certitudes, bornes, copies, altérations, doublons, refus, filtres,
provenance et export. Le banc numérique est décrit dans
[le README du plugin](../../plugins/calibration/README.md).

**À vérifier visuellement, dans un vault d'essai, avant fusion :**

1. Ouvrir Calibration : fenêtre au premier plan, défilement, fermeture et Échap,
   boutons accessibles, texte lisible à petite largeur. À vide : « Non calculé ».
2. Créer une prédiction ouverte à p=0,8, échéance demain ou plus tard. Préparer sa
   copie : vérifier les trois états de chaque borne et la saisie de date activée
   seulement pour « Date connue ». Annuler ne crée pas de copie.
3. Confirmer avec bornes ouvertes : une copie estampillée est créée. Ouvrir la
   copie Markdown ; tenter une seconde inscription ne doit jamais l'écraser.
4. Résoudre la prédiction « oui », avec date du jour et preuve dans un scénario
   d'essai. Actualiser : n=1, Brier=0,04, log loss≈0,2231, point (0,8;1).
5. Créer séparément un pari à p=1, copié avant résolution puis résolu « non » :
   log loss ∞. Vérifier effectifs par domaine et horizon, tableau et graphique.
6. Tester un pari non inscrit, un résultat indéterminable et une probabilité
   modifiée après copie : exclusions explicites, jamais comptées comme zéros.
7. Filtrer une date avec bornes inconnues : exclusion expliquée. Retirer la date :
   retour du pari. Exporter : rapport, classes, preuves et exclusions lisibles.
8. Désactiver Calibration et recharger : les objets restent utilisables.
   Réactiver : les copies et rapports restent présents.

**Limites :** Windows/PowerShell et affichage réel non exécutés ici. Navigateur
local indisponible ; téléchargement échoué ; navigateur distant refusant localhost.
Les tests de DOM de Constat ne remplacent pas ce contrôle. Livraison en revue.

## Hors périmètre

E9, synchronisation/verrouillage réparti, horodatage certifié, reconstruction des
connaissances historiques, scoring des décisions et modifications de Constat.
