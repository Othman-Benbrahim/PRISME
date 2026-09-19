# 0037 · Distribution Windows E9

- **Statut** : mise en œuvre ; validation Windows et publication à confirmer
- **Date** : 2026-09-19
- Prolonge [0030](0030-dependances-compilees-dans-l-executable.md) et [0036](0036-guides-plugins-et-perimetre-e9.md).

## Périmètre

Une archive Windows x64 réunit `PRISME.exe`, `_internal/`, `plugins/`,
`guides-plugins/`, `mcp/`, les documents et les licences. L'exécutable utilise le
navigateur par défaut pour son interface ; E9 ne remplace pas l'interface par une
nouvelle application graphique. Python et Node ne sont requis que pour construire
et tester, jamais pour lancer la distribution.

Les neuf plugins sont des fichiers externes. En retirant physiquement `plugins/`,
on retrouve les fonctions du cœur. Les bibliothèques tierces des plugins, notamment
ONNX Runtime, tokenizers et DDGS, sont gelées dans `_internal/`, conformément à 0030.
Cela ne rend aucun plugin natif du cœur. Le gestionnaire n'exécute pas pip. Ajouter
un nouveau plugin exigeant une bibliothèque tierce non livrée demandera une nouvelle
construction ou une distribution compatible de cette bibliothèque.

Le modèle e5 reste téléchargé ou choisi depuis le plugin, dans le profil utilisateur.
Aucun poids de modèle ni note personnelle n'entre dans l'archive. Maigret et Sherlock
restent des programmes externes facultatifs, accessibles dans PATH ; l'exécutable
PRISME ne se fait jamais passer pour l'interpréteur Python de ces outils.

## Construction et contrôles

`packaging/construire-windows.ps1` crée son environnement de construction, exécute
les tests Python et Constat, puis `packaging/construire.py` construit avec PyInstaller
**onedir**. Le répertoire de sortie doit être neuf et les fichiers suivis committés.
Seuls les fichiers suivis sélectionnés sont copiés : pas de `.env`, cache, dépendances
Node de développement ou tests dans les plugins distribués. Les licences des plugins,
y compris celle de Constat, sont conservées. L'archive des sources du commit exact
accompagne l'archive binaire. Les versions réellement installées sont consignées.

Avant de créer le ZIP, le build lance le binaire depuis un autre dossier, dans des
profils temporaires, avec un PATH sans Python ni Node. Il vérifie les neuf plugins,
leurs assets, l'authentification, la création du vault, une inférence ONNX et DPAPI
sur Windows. Il retire ensuite physiquement `plugins/` et vérifie le cœur seul.
Enfin, un vrai serveur HTTP et le mode `PRISME.exe --mcp` vérifient le démarrage et
l'initialisation MCP. Le diagnostic ONNX utilise un modèle minuscule créé pour le test,
absent de la livraison ; il ne prétend pas mesurer la qualité du modèle e5.

La CI Windows produit un artefact de contrôle. Un test Linux supplémentaire ne valide
pas Windows. La publication de la release attend la vérification visuelle sur Windows,
avec le modèle et les services choisis par l'utilisateur. Les sommes SHA-256 contrôlent
l'intégrité de l'archive ; elles ne constituent pas une signature de l'éditeur.

## Après E9

Le transfert direct Constat → Calibration et les apports éventuels d'Utopia
(sources attachées aux affirmations, historique, contradictions) restent hors E9.
Le type Prédiction appartient au cœur ; les calculs Brier, log loss et les mesures de
calibration appartiennent au plugin Calibration. Ces responsabilités ne sont pas fusionnées.
