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
| E6 | `e6-api-agents` | API HTTP locale à clés, droits par clé, journal | Fait |
| — | `sources-ia-note` | Bouton « Sources IA » : analyse de la note ouverte seule | Fait |
| E7 | `e7-embeddings` | Fournisseurs API et Ollama dans le cœur, fusion RRF, plancher de pertinence | Fait |
| — | `plugin-embeddings-locaux` | Plugin ONNX : modèle e5 local, rien ne sort de la machine | En revue |
| E12 | `e12-racines` | Plusieurs racines de vault ; agents bornés à la principale | En revue |
| E13 | `e13-arbre` | Recherche en arbre : propagation par les liens, élagage avant réponse | À faire |
| E10 | `e10-mcp` | Adaptateur MCP au-dessus de `/api/v1/` | À faire |
| E11 | `e11-types-objets` | Décision, hypothèse, prédiction, entité, tâche ; paramétrage par type | À faire |
| E9 | `e9-publication` | Import d'un vault V1, guide des ruptures, première version publique | À faire |

L'ordre est **E12 → E13 → E10 → E11 → E9**. E12 passe devant parce qu'elle touche `safe_path`,
la fonction la plus sensible du projet : plus elle arrive tard, plus il y a de code à
revérifier contre elle. La place de E9 est fixée par [la décision 0027](decisions/0027-ordre-des-etapes-restantes.md) :
la publication vient en dernier parce qu'elle sert des utilisateurs qui n'existent pas encore,
là où E10 et E11 servent l'auteur tout de suite.

## Hors périmètre

Ce qui a été examiné et écarté, ou reporté sans étape. Rien ici n'est oublié : c'est
décidé, ou explicitement en attente.

| Sujet | État |
|---|---|
| Plugin de calibration (Brier, log loss, courbes) | Reporté après E11 — [0025](decisions/0025-calibration-en-plugin.md). Le cœur fournira le type Prédiction, le plugin fera le calcul. |
| Horloge du monde active | S'activera avec ce plugin — [0026](decisions/0026-horloge-du-monde-activee.md). Les champs sont réservés depuis E3, aucune migration à prévoir. |
| Mécanisme de gel des objets | Prévu dans le modèle (0017), non implémenté. |
| Seuil d'entrée directe par type | Sans objet tant qu'il n'y a qu'un type (0021). |
| Rejets synchronisés avec le vault | Décidé — [0024](decisions/0024-synchronisation-entre-machines.md) — reste à appliquer. |
| Données de plugins dans le vault | À trancher plus tard (0024). |
| Modèle de décision hébergé (type Jev) | Examiné, écarté : cloud obligatoire, poids fermés, calibration annoncée moindre hors anglais. Les principes sont reproductibles sans dépendance payante. |
| Verrouillage réparti, écritures concurrentes | Assumé : le dernier qui écrit gagne, `.trash/versions/` sert de filet (0024). |
| Chiffrement des secrets hors Windows | DPAPI est Windows seul (0023). À traiter en E9 si la publication vise macOS et Linux. |
| Épreuve du réel : vault de l'auteur, build PyInstaller | Jamais faits. Le plugin ONNX rend la question du `--onefile` avec bibliothèque compilée plus pressante. À planifier avant E9. |
