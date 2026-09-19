# Constat intégré — remplacement de la livraison de l’extension

## Objectif

Donner accès à Constat directement depuis PRISME, selon la correction de l’auteur
(0035), en reprenant la structure et les calculs de son add-on. Calibration reste
une livraison séparée ; l’installation de l’extension n’est pas un prérequis.

## Fichiers touchés

Ajouts : `plugins/constat/`, `tests/test_constat_integre.py`, décision 0035, cette fiche.
Modifications : service des ressources de plugins (modules sous `web/` seulement),
route de proposition locale des prédictions, liste attendue des plugins livrés,
documentation de suivi. Aucun fichier supprimé, aucun calcul ajouté au cœur.
Aucune dépendance Python supplémentaire. Node/linkedom sont des dépendances de test.
`vault.py`, `core.css`, l’API des agents et le plugin Calibration ne sont pas modifiés.

## Ruptures

La livraison `Constat-integration-PRISME.zip` et son script 21 correspondaient à
l’extension. Ce nouveau ZIP les remplace pour l’usage souhaité dans PRISME.
Ne pas fusionner la PR de l’extension pour installer cet espace. Si elle est déjà
fusionnée, cela n’empêche pas le plugin de fonctionner ; aucun retour arrière
ni suppression de dossier Firefox n’est effectué par cette livraison.

Les anciens dossiers Firefox ne sont pas transférés automatiquement. Les nouvelles
données appartiennent au profil PRISME. L’export JSON de cet espace inclut les textes.
Le plugin peut être installé sur E11, avec ou sans Calibration déjà fusionné.
Le test inclut Calibration dès que son manifeste est installé, indépendamment de
la variante de base reconnue. Il vérifie aussi son activation et sa ressource UI.
Le chargeur ignore les dossiers sans manifeste qui sont vides ou ne contiennent
que des caches Python, résidus possibles après annulation d’une livraison.
Un dossier contenant encore du code sans manifeste reste incompatible.

## Tester

```powershell
$env:PYTHONHASHSEED = "0"
python -m unittest discover -s tests
npm ci --prefix plugins/constat --ignore-scripts --no-audit --no-fund
npm test --prefix plugins/constat
```

Résultats de préparation : **403 tests Python, 384 réussis, 19 ignorés** sur E11 +
Constat ; **134 tests Node réussis**, dont 128 tests repris et 6 tests d’intégration.
Le test d’interaction exerce chargement, création du dossier fictif, rendu du relevé,
validation ACH, trois champs vides et proposition unique malgré un double envoi.
Avec Calibration installé en plus : **423 tests Python, 404 réussis, 19 ignorés**.
La suite Python exerce la vraie route de file, la provenance, l’acceptation séparée,
la persistance, les conflits de révision, les bornes de vault et les ressources.
Trois tests supplémentaires couvrent les dossiers résiduels, le maintien de
l’erreur sur un plugin incomplet et le chargement des plugins livrés après annulation.

Une première exécution a révélé la sensibilité du faux fournisseur vectoriel E7
au hash aléatoire Python (test de hors-sujet, sans modification de ce code).
`PYTHONHASHSEED=0`, également fixé par le script, rend ce banc reproductible.
Aucune amélioration de précision analytique n’est revendiquée par ce portage.

## Vérification visuelle à faire avant fusion

1. Lancer `python prisme.py`, ouvrir PRISME et cliquer **Constat** dans sa barre.
   Vérifier taille de la fenêtre, défilement, fermeture « Revenir au vault ».
2. Cliquer **Créer un dossier de démonstration**. Trois pièces fictives et leur
   relevé doivent apparaître. Aucun appel de modèle, aucune note créée dans le vault.
3. Repérer l’étape ACH fictive. Avant validation : pas de bouton de versement.
   Cliquer **Valider l’étape 5**, puis **Verser comme prédiction dans PRISME**.
4. Vérifier les trois champs vides. Saisir p=0,8, échéance future, condition observable.
   Déposer : une proposition dans la file PRISME, aucun objet avant acceptation.
5. Revenir au vault, accepter la proposition. Si Calibration est installé, y inscrire
   la copie avant le jour d’échéance, puis résoudre le scénario fictif et vérifier le score.
6. Dans Constat, ajouter une source : relevé historique signalé, analyses/versement
   suspendus jusqu’au nouveau relevé. Une nouvelle analyse attend à nouveau validation.
7. Tester une vraie note du vault et un HTML enregistré. Vérifier titres, accents,
   métadonnées inconnues, motifs de cotation et limites des absences sur du texte brut.
8. Exporter un rapport Markdown et le JSON complet, fermer/réouvrir PRISME : dossiers
   conservés. Restaurer le JSON crée un autre dossier sans écraser l’original.
9. Modèle configuré : préparer une étape, lire les messages, annuler (aucun appel),
   puis lancer explicitement. Vérifier trace brute, sortie et correction non validée.

Limites : le navigateur de vérification refuse localhost (`ERR_BLOCKED_BY_CLIENT`).
Les interactions DOM sont testées, mais l’apparence réelle et Windows/PowerShell
restent à vérifier sur la machine de l’auteur. La PR est donc créée en brouillon.

## Hors périmètre

E9, scoring (Calibration séparé), capture d’onglets et recherche Exa dans ce portage,
transfert automatique des anciens dossiers Firefox, chiffrement des dossiers,
horodatage probant et synchronisation distribuée. Détails dans le README du plugin.
