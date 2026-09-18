# Architecture du code

État après l'étape E2. Mis à jour à chaque étape qui déplace des responsabilités.

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

## Interface `prisme_core/web/`

`index.html` contient uniquement la structure HTML. Les styles sont dans `css/`, le
comportement dans `js/`, un fichier par zone. L'ordre des balises `<script>` compte :

1. `token.js` : jeton de session, installé avant tout appel à l'API
2. `helpers.js`, `tabs.js`, `editor.js`, `explorer.js`, `tags.js`, `backlinks.js`,
   `search.js`, `graph.js`, `synthesis.js`, `ai-selection.js`, `link-suggest.js`, `ai-file.js`,
   `plugin-manager.js`, `gutter.js` (numéros de ligne), `history.js` (annuler/rétablir),
   `find-in-note.js` (recherche dans la note)
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
