# Feuille de route

Chaque étape dépend des précédentes. Une étape = une branche = une pull request vers `main`.

| Étape | Branche | Objet | État |
|---|---|---|---|
| Base | `main` (étiquette `base-v1`) | Import du code de Second Brain V1, sans modification | Fait |
| E8 | `e8-decoupage-coeur` | Découpage du cœur et de l'interface, renommage PRISME, aucune nouvelle fonctionnalité | En revue |
| E1 | `e1-api-plugins` | `prisme_core.api`, hooks synchrones, gestionnaire de plugins, migration des plugins | À faire |
| E2 | `e2-index-sqlite` | Index SQLite FTS5 dans le profil, double granularité fichier + segment | À faire |
| E3 | `e3-provenance` | Frontmatter `prisme_*`, identifiants posés au besoin | À faire |
| E4 | `e4-engram` | Contrat d'extraction, identité des passages, importeurs légers | À faire |
| E5 | `e5-objets` | File de validation, objet Source | À faire |
| E6 | `e6-api-agents` | API HTTP locale à clés | À faire |
| E7 | `e7-embeddings` | Fournisseurs API et Ollama dans le cœur, plugin ONNX | À faire |
| E9 | `e9-publication` | Import d'un vault V1, guide des ruptures, première version publique | À faire |
