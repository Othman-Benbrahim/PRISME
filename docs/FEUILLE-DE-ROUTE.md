# Feuille de route

**Correction de périmètre (0035)** : Constat s’utilise directement dans PRISME,
sous forme de plugin. L’extension Firefox n’est pas requise. Calibration reste
séparé, avec l’horloge du monde ; E11 ne contient PAS ses calculs.

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
| — | `plugin-embeddings-locaux` | Plugin ONNX : modèle e5 local, rien ne sort de la machine | Fait |
| E12 | `e12-racines` | Plusieurs racines de vault ; agents bornés à la principale | Fait |
| E13 | `e13-arbre` | Recherche en arbre : propagation par les liens, élagage avant réponse | Fait |
| E10 | `e10-mcp` | Adaptateur MCP au-dessus de `/api/v1/` | Fait |
| E11 | `e11-types-objets` | Décision, hypothèse, prédiction, entité, tâche ; paramétrage par type. **Ne contient PAS le calcul de calibration** | Fusionnée (PR #18) |
| — | `plugin-calibration` | Calibration en plugin, copies de référence et horloge du monde | Implémenté — PR #19 |
| — | `plugin-constat-integre` | Constat dans PRISME : dossiers, ACH et propositions de prédiction | Implémenté — PR #20 |
| — | `docs-guides-plugins` | Guides Markdown des neuf plugins dans un dossier séparé | Étape préalable à E9 |
| E9 | `e9-publication` | Application Windows `.exe`, plugins externes et guides réunis dans une archive de release | En cours — build et contrôles, publication après validation Windows |

### La chaîne Prédiction — ne pas fusionner les trois pièces

1. **E11** : le cœur fournit le type Prédiction (probabilité, horizon, condition de
   résolution, résultat observé). **Aucun calcul de calibration dans E11.**
2. **Plugin de calibration** ([0025](decisions/0025-calibration-en-plugin.md)), après
   E11 : Brier, log loss et calibration par domaine/horizon dans `plugins/`, avec ses
   éventuelles dépendances. Il active l'**horloge du monde** ([0026](decisions/0026-horloge-du-monde-activee.md)) :
   champs réservés depuis E3, sans migration, mais branchement explicite.
3. **Constat intégré** ([0035](decisions/0035-constat-integre.md)), après E11 :
   dossiers et ACH dans un plugin PRISME, sans extension ni clé d’agent.
   L’auteur formule le pari ; la file PRISME attend sa validation.

**Périmètre confirmé par l'auteur** : les guides des plugins précèdent E9. E9
porte uniquement sur la distribution Windows et sa release : `PRISME.exe`, un
dossier `plugins/` externe et le dossier `guides-plugins/`. Sans le dossier de
plugins, le cœur doit fonctionner seul. Les dépendances nécessaires doivent être
livrées et vérifiées ; les plugins ne sont pas compilés dans le cœur.
Voir [0036](decisions/0036-guides-plugins-et-perimetre-e9.md).

L'ordre est **E12 → E13 → E10 → E11 → guides des plugins → E9**. E12 passe devant parce qu'elle touche `safe_path`,
la fonction la plus sensible du projet : plus elle arrive tard, plus il y a de code à
revérifier contre elle. La place de E9 est fixée par [la décision 0027](decisions/0027-ordre-des-etapes-restantes.md) :
la publication vient en dernier parce qu'elle sert des utilisateurs qui n'existent pas encore,
là où E10 et E11 servent l'auteur tout de suite.

## Hors périmètre

Ce qui a été examiné et écarté, ou reporté sans étape. Rien ici n'est oublié : c'est
décidé, ou explicitement en attente.

| Sujet | État |
|---|---|
| Plugin de calibration (Brier, log loss, courbes) | Implémenté dans `plugin-calibration` (PR #19) — [0025](decisions/0025-calibration-en-plugin.md). E11 fournit le type, seul le plugin calcule. |
| Constat intégré dans PRISME | Implémenté — [0031](decisions/0031-constat-source-des-hypotheses.md). Plugin intégré, dossiers et ACH ; proposition interne en file, sans clé d’agent (PR #20) — voir [0035](decisions/0035-constat-integre.md). |
| Horloge du monde active | Branchée par le plugin (PR #19) — [0026](decisions/0026-horloge-du-monde-activee.md). Les champs sont réservés depuis E3, aucune migration à prévoir. |
| Mécanisme de gel des objets | Prévu dans le modèle (0017), non implémenté. |
| Seuil d'entrée directe par type | Implémenté en E11 (0033). Aucun signal automatique défini pour les cinq nouveaux types. |
| Rejets synchronisés avec le vault | Décidé — [0024](decisions/0024-synchronisation-entre-machines.md) — reste à appliquer. |
| Données de plugins dans le vault | À trancher plus tard (0024). |
| Modèle de décision hébergé (type Jev) | Examiné, écarté : cloud obligatoire, poids fermés, calibration annoncée moindre hors anglais. Les principes sont reproductibles sans dépendance payante. |
| Verrouillage réparti, écritures concurrentes | Assumé : le dernier qui écrit gagne, `.trash/versions/` sert de filet (0024). |
| Chiffrement des secrets hors Windows | DPAPI est Windows seul (0023). À traiter en E9 si la publication vise macOS et Linux. |
| Découpage de `core.css` | **Pressant.** 19 707 caractères sur un plafond de 20 000 : il reste 293 caractères de marge. La prochaine étape qui y touche fera sauter le garde-fou d'E8. À découper par zone (mise en page, éditeur, fenêtres) au prochain passage dans ce fichier. |
| Build PyInstaller | Tranché — [0030](decisions/0030-dependances-compilees-dans-l-executable.md) : `--onedir`, `onnxruntime` et `tokenizers` gelés dans l'exécutable, modèle e5 toujours téléchargé dans le profil. Reste à construire et à vérifier. |
| Adaptateur MCP branché sur un vrai Claude Code | Jamais fait. Les tests reproduisent le protocole fidèlement (sous-processus, JSON-RPC), mais un client réel a ses exigences propres. Premier essai à faire. |
| Épreuve du réel : vault de l'auteur | Les fonctions ont été essayées et répondent. L'usage soutenu sur le vault réel, lui, reste à faire — c'est le seul essai qui peut invalider ce que 359 tests confirment entre eux. |
