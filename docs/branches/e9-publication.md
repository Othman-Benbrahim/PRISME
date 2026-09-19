# E9 · Distribution Windows

Branche : `e9-publication`. Décision : [0037](../decisions/0037-distribution-windows-e9.md).

## Résultat attendu

Extraire toute l'archive dans un dossier accessible en écriture. Double-cliquer
`PRISME.exe` ouvre l'interface dans le navigateur. Garder `_internal/` à côté de
l'exécutable : ce dossier contient son environnement d'exécution. Garder `plugins/`
pour les neuf plugins et `guides-plugins/` pour leurs guides. Fermer PRISME avec
Ctrl+C dans sa console avant de déplacer ou remplacer ces dossiers.

Aucun Python, Node, serveur IA ni modèle n'est installé par le lancement. Les services
IA restent à configurer ; un modèle local nécessite le fournisseur correspondant.
Les ressources d'interface servies par CDN restent celles de la version source : E9
ne garantit pas une interface entièrement hors réseau lors du premier chargement.

## Vérification visuelle avant publication

Utiliser un nouveau profil et un vault d'essai, jamais déplacer le vault habituel.

1. Au premier lancement : l'assistant s'affiche, un dossier de notes peut être choisi,
   une note accentuée peut être créée, enregistrée, fermée et retrouvée après relance.
2. Plugins : les neuf modules sont actifs ; ouvrir les panneaux ArXiv, DDG, Context,
   Prompts, RSS, OSINT, Embeddings, Constat et Calibration. Vérifier l'absence de panneau
   vide ou d'erreur JavaScript dans la console du navigateur.
3. Constat : suivre son [dossier de démonstration](../../guides-plugins/constat.md),
   ouvrir la matrice ACH, modifier une évaluation et retrouver le dossier après relance.
4. Calibration : suivre [le premier score](../../guides-plugins/calibration.md).
   Vérifier une prédiction résolue et un score chiffré. E9 ne change pas le transfert
   depuis Constat et n'invente pas de résultat observé.
5. Embeddings : télécharger ou sélectionner e5, vérifier l'état prêt, vectoriser
   quelques notes et obtenir une recherche sémantique. Les bibliothèques sont livrées,
   le modèle reste distinct. Le build a déjà testé le calcul ONNX sur un modèle de contrôle.
6. Selon les services utilisés : tester une recherche DDG/ArXiv, un flux RSS et une
   réponse du fournisseur IA configuré. Les outils externes Maigret/Sherlock sont facultatifs.
7. Fermer PRISME. Renommer `plugins` en `plugins-desactives`, relancer : le cœur doit
   fonctionner, sans boutons des plugins. Fermer, restaurer `plugins`, relancer.
8. Agents : générer une configuration MCP ; sa commande est le chemin de `PRISME.exe`,
   avec l'argument `--mcp`. Un client MCP installé séparément peut s'y connecter.

## Construction et release

Le script `packaging/construire-windows.ps1` s'exécute sous PowerShell 5.1 ou 7 avec
Git, Python 3.12 x64 et Node 22. Il crée un environnement isolé ; aucune activation
PowerShell n'est nécessaire. Les erreurs de test ou de compilation interrompent la
création de l'archive. Les artefacts de la CI Windows sont des candidats à contrôler,
pas des releases déjà publiées.

Après validation visuelle et fusion de la PR, construire le commit final de `main`.
Attacher à la même release le ZIP Windows, le ZIP des sources et `SHA256SUMS.txt` issus
de cette construction. Le tag doit viser le commit inscrit dans `construction.json`.
Ne pas attacher une archive ancienne à un tag pointant vers un autre commit.
La publication n'est pas automatique dans cette branche.
