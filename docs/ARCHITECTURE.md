# Architecture du code

État après l'étape E4. Mis à jour à chaque étape qui déplace des responsabilités.

## Lancement

- `python prisme.py` ou `python -m prisme_core` depuis la racine du dépôt.
- `pyinstaller packaging/PRISME.spec` produit `dist/PRISME.exe` ; le dossier `plugins/`
  se pose à côté de l'exe.

## Package `prisme_core/`

| Module | Rôle |
|---|---|
| `__init__.py` | Nom et version |
| `paths.py` | Emplacements : ressources `web/`, dossier de l'application, profil `~/.prisme/` (surchargeable par `PRISME_DATA_DIR`), reprise de la config V1 |
| `config.py` | Lecture et écriture de `config.json` (UTF-8), clé d'API chiffrée au repos |
| `secrets.py` | Chiffrement DPAPI et coffre des secrets de plugins (`secrets.json`) |
| `envfile.py` | Chargement des fichiers `.env` |
| `vault.py` | Racine autorisée, garde de chemin, corbeille, instantanés, parcours des `.md` |
| `markdown.py` | Extraction des liens et des tags, résolution des références |
| `frontmatter.py` | Lecture et écriture de l'en-tête YAML, sans dépendance |
| `engram/` | **Ingestion des sources** : `contrat.py` (vérification et empreintes), `extracteurs.py` (ChatGPT, Claude, Mistral, texte, HTML, JSON), `identite.py` (identité des passages), `notes.py` (rendu, parties, archive), `ingestion.py` (import idempotent, registre) |
| `agents/` | **Accès des agents** : `cles.py` (trousseau, empreintes, droits), `garde.py` (authentification par clé, décorateur de droit), `journal.py` (journal JSONL borné) |
| `vecteurs/` | **Recherche sémantique** : `contrat.py` (interface fournisseur, registre), `fournisseurs.py` (API compatible OpenAI, Ollama), `quantification.py` (binarisation, Hamming, cosinus, RRF), `magasin.py` (base des vecteurs, par empreinte de segment), `vectorisation.py` (mise à jour incrémentale), `recherche.py` (fusion, plancher, repli) |
| `arbre/` | **Recherche en arbre** : `parcours.py` (amorce, propagation par les liens et backlinks, décroissance, plafonds, budget), `contexte.py` (carte des relations, assemblage du contexte, `comparer()` — la mesure qui a corrigé la justification de l'étape) |
| `objets/` | **Objets conceptuels** : `detection.py` (repérage et normalisation des URL, DOI, arXiv, ISBN), `file.py` (file de validation et rejets mémorisés), `sources.py` (objets Source comme notes du vault, lots, lien ENGRAM), `balayage.py` (entrée directe, propositions de l'IA, accepter / rejeter / fusionner) |
| `provenance.py` | Identifiants, horloge d'enregistrement, estampillage des notes produites par une machine, validation des champs saisis à la main |
| `index/` | **Index SQLite** : `store.py` (base et schéma), `segmenter.py` (découpage), `resolver.py` (résolution des liens), `indexer.py` (mise à jour), `search.py` (recherche, tags, graphe, backlinks) |
| `providers.py` | Fournisseurs IA (OpenAI-compatibles, Anthropic), appel générique |
| `api.py` | **API publique des plugins** (`PluginContext`, version 1) |
| `hooks.py` | Événements synchrones avec délai maximal |
| `plugins.py` | Registre, chargement, aiguilleur `/api/plugins/<id>/`, service des fichiers d'interface, assemblage de la page |
| `plugin_install.py` | Vérification des archives, installation à chaud, désinstallation |
| `app.py` | Création de l'application Flask et lancement |
| `routes/security.py` | Contrôle de l'en-tête `Host` et jeton de session `X-Prisme-Token` |
| `routes/pages.py` | Page principale, liste des plugins |
| `routes/setup.py` | Premier lancement, configuration, diagnostic, modèles |
| `routes/ai.py` | Appels IA simples, flux SSE, synthèse de dossier |
| `routes/files.py` | Fichiers du vault, graphe, backlinks |
| `routes/search.py` | Recherche plein texte, tags, état et reconstruction de l'index |
| `routes/plugin_manager.py` | Gestionnaire de plugins : liste, installation, activation, secrets |
| `routes/engram.py` | Import de sources : inspection, import, registre, contrôle |
| `routes/objets.py` | Objets Source : balayage, statuts, lots, file de validation, rejets |
| `routes/agent_api.py` | Surface `/api/v1/` des agents : lecture, proposition, écriture |
| `routes/agents.py` | Gestion du trousseau depuis l'interface |
| `routes/racines.py` | Racines du vault : déclarer, retirer, promouvoir |
| `routes/vecteurs.py` | Recherche sémantique : état, test, vectorisation, paramétrage |
| `routes/arbre.py` | Recherche en arbre : construire (sans modèle), puis répondre sur les nœuds cochés |
| `api.py` (embeddings) | `register_embeddings`, `EmbeddingProvider`, `EmbeddingUnavailable` : la porte par laquelle un plugin apporte ses propres vecteurs |

## Interface `prisme_core/web/`

`index.html` contient uniquement la structure HTML. Les styles sont dans `css/`, le
comportement dans `js/`, un fichier par zone. L'ordre des balises `<script>` compte :

1. `token.js` : jeton de session, installé avant tout appel à l'API
2. `helpers.js`, `tabs.js`, `editor.js`, `explorer.js`, `tags.js`, `backlinks.js`,
   `search.js`, `graph.js`, `synthesis.js`, `ai-selection.js`, `link-suggest.js`, `ai-file.js`,
   `plugin-manager.js`, `gutter.js` (numéros de ligne), `history.js` (annuler/rétablir),
   `find-in-note.js` (recherche dans la note), `provenance.js` (fiche de provenance),
   `engram.js` (import de sources), `objets.js` (sources citées et file de validation),
   `agents.js` (clés d'accès et journal), `vecteurs.js` (recherche sémantique),
   `racines.js` (racines du vault), `arbre.js` (recherche en arbre)
3. les plugins actifs, un fichier chacun (`/plugins/<id>/ui.js`)
4. `mindmap.js`, `layout.js`, `settings.js`, `init.js`, `onboarding.js`, `ai-stream.js`

La page est réassemblée à chaque chargement : modifier un fichier de `web/` puis
rafraîchir le navigateur suffit.

## Profil utilisateur `~/.prisme/`

| Élément | Contenu |
|---|---|
| `config.json` | Réglages ; clé d'API chiffrée sous Windows |
| `secrets.json` | Secrets des plugins, chiffrés sous Windows |
| `plugins.json` | État des plugins : activé, source, empreintes, date d'installation |
| `plugins/<id>/` | Données privées de chaque plugin |
| `index/<empreinte>.db` | Index d'un vault, avec `vaults.json` (empreinte → chemin) ; supprimable, il se reconstruit |
| `engram/engram.json` | Registre des sources importées ; reconstructible depuis les notes |
| `objets/file.json` | File de validation et rejets mémorisés — hors du vault, par construction |
| `agents/cles.json` | Trousseau des agents : empreintes seules, jamais les clés |
| `agents/journal.jsonl` | Journal des appels d'agent ; survit à la révocation des clés |
| `vecteurs/<empreinte>.db` | Vecteurs d'un vault, par empreinte de segment ; **séparés de l'index**, qui se reconstruit sans les détruire |
| `staging/` | Archives vérifiées en attente de confirmation (effacées après une heure) |
| `corbeille-plugins/` | Plugins désinstallés ou remplacés |

## Plugins

Un plugin est chargé seulement si son manifest déclare `api_version: 1` et un `id`
identique au nom de son dossier. Ses routes ne sont pas enregistrées dans Flask : un
aiguilleur unique (`/api/plugins/<id>/<chemin>`) les résout dans une table propre au
plugin. C'est ce qui permet d'installer, d'activer et de désactiver sans redémarrer.

## Index de recherche

Les `.md` restent la source de vérité ; l'index n'est qu'un cache dérivé.

- **Deux granularités** : une ligne par fichier (liens, tags, graphe) et une
  ligne par segment (recherche). Un segment = un titre de niveau 1 à 3, ou un
  groupe de paragraphes pour une note sans titre.
- **Mise à jour incrémentale** : un fichier n'est relu que si sa date ou sa
  taille a changé, et réindexé que si son contenu a changé ; dans un fichier
  modifié, seuls les segments dont l'empreinte a changé sont réécrits.
- **Écritures faites par PRISME** : prises en compte immédiatement
  (`notify_changed`). **Écritures faites ailleurs** (Obsidian) : vues à la
  vérification suivante, au plus deux secondes après.
- **Gros vault** (plus de 5 000 notes) : la construction et les vérifications
  passent en arrière-plan ; la recherche répond avec ce qui est déjà indexé.
- **Reconstruction complète** : construite dans un fichier à part, qui remplace
  l'ancien en une seule opération, une fois qu'aucune lecture n'est en cours.
