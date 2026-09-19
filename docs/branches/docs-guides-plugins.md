# Guides des plugins — étape préalable à E9

## Objectif

Permettre d'utiliser les neuf plugins depuis leurs écrans actuels, sans devoir
reconstituer les étapes à partir de notices techniques ou historiques. Les guides
expliquent les résultats et les limites, en particulier les validations Constat,
la copie des paris avant résolution et l'activation du fournisseur ONNX.

## Fichiers touchés

Créés : `guides-plugins/README.md`, neuf guides individuels, décision 0036 et cette fiche.
Modifiés : README principal, feuille de route, index des décisions et avertissement
de lecture dans l'ancienne notice OSINT. Aucun code d'exécution modifié ou supprimé.

## Ruptures

Aucune rupture de fonctionnement. Le périmètre d'E9 est explicitement restreint à
la distribution Windows et sa release, selon la demande de l'auteur. Les guides
seront livrés à côté des plugins. La construction de l'exécutable reste à faire.

## Tester

Contrôler qu'un guide correspond à chaque `plugins/*/manifest.json`, que le sommaire
les relie tous et que leurs liens locaux existent. Lire les tableaux et blocs de
commandes dans le rendu Markdown de GitHub. Comparer les libellés à l'interface.
Les scores d'exemple, les préalables d'étapes et les limites ont été confrontés au code.

La livraison vérifie les liens et le diff complet, y compris les fichiers nouveaux.
Elle ne relance pas les suites d'application pour ces seules modifications Markdown.
Les services externes et leur disponibilité n'ont pas été testés dans cette étape.

## Hors périmètre

Compilation `.exe`, dépendances de la distribution, publication de release,
modification des plugins et fonctionnalités nouvelles. Ces guides documentent la
version source actuelle et distinguent les exigences de la future distribution.
