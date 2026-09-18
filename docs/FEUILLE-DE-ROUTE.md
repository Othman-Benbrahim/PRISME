# Feuille de route

Chaque étape dépend des précédentes. Une étape = une branche = une pull request vers `main`.

| Étape | Branche | Objet | État |
|---|---|---|---|
| Base | `main` (étiquette `base-v1`) | Import du code de Second Brain V1, sans modification | Fait |
| E8 | `e8-decoupage-coeur` | Découpage du cœur et de l'interface, renommage PRISME, aucune nouvelle fonctionnalité | Fait |
| E1 | `e1-api-plugins` | `prisme_core.api`, hooks synchrones, gestionnaire de plugins, migration des plugins, secrets chiffrés, fiches de décision | Fait |
| E2 | `e2-index-sqlite` | Index SQLite FTS5 dans le profil, double granularité fichier + segment, questions de référence | Fait |
| — | `confort-editeur` | Numéros de ligne, annuler/rétablir, recherche dans la note | Fait |
| E3 | `e3-provenance` | Frontmatter `prisme_*`, identifiants posés au besoin, horloge d'enregistrement | Fait |
| — | `provenance-editable` | Fiche de provenance modifiable, choix des sources, pose d'identifiant | Fait |
| — | `dialogues-interface` | Création de fichier et confirmations dans l'interface, sans popup | Fait |
| E4 | `e4-engram` | Contrat d'extraction, identité des passages, importeurs légers (ChatGPT, Claude, Mistral, texte, HTML) | Fait |
| E5 | `e5-objets` | File de validation, entrée directe des imports en masse, objet Source | Fait |
| E6 | `e6-api-agents` | API HTTP locale à clés, droits par clé, journal | En revue |
| E7 | `e7-embeddings` | Fournisseurs API et Ollama dans le cœur, plugin ONNX | À faire |
| E9 | `e9-publication` | Import d'un vault V1, guide des ruptures, première version publique | À faire |
