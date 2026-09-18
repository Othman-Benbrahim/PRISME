# Ruptures par rapport à la base V1

Journal cumulatif des changements incompatibles avec Second Brain V1 (`base-v1`).
Chaque étape ajoute sa section. Ce fichier servira de base au guide de passage.

<!-- Les étapes ajoutent leurs sections ci-dessous, la plus récente en haut. -->

## E5 — Objets Source et file de validation

Étape uniquement additive : rien de ce qui existait ne change de comportement.

| Nouveauté | Détail |
|---|---|
| Dossier créé dans le vault | `Objets/Sources/` — un `.md` par référence citée, lisible dans Obsidian |
| En-tête des objets | `prisme_reference`, `prisme_genre`, `prisme_statut` (`citee` / `ingeree`), `prisme_relu`, `prisme_lot`, `prisme_cite_par`, `prisme_alias`, `prisme_fusions` |
| Routes | `/api/objets/sources`, `/balayer`, `/ia`, `/relu`, `/lier`, `/supprimer`, `/statuts`, `/lot/annuler`, `/note`, `/file`, `/file/accepter`, `/file/rejeter`, `/file/fusionner`, `/file/defusionner`, `/rejets/oublier` |
| File de validation | `~/.prisme/objets/file.json` — propositions et rejets mémorisés, hors du vault |
| Interface | Bouton 🔖 Sources citées ; marqueur 🔖 dans l'en-tête de l'éditeur pour une note qui cite des objets non relus |
| Dialogues | `demanderTexte()` accepte `libre: true` : une réponse vide est acceptée (champ facultatif) |

Le type `source` existait déjà dans `prisme_core.provenance.TYPES` : aucun champ
nouveau n'est ajouté au vocabulaire de provenance. Aucun changement de schéma
d'index : rien n'est reconstruit.

## Dialogues dans l'interface

| Avant | Après |
|---|---|
| ＋ ouvrait un `prompt` du navigateur | Ligne de saisie dans l'explorateur (`Entrée` valide, `Échap` annule) |
| Confirmations par `confirm` | Fenêtre de PRISME (`confirmer()`), bouton rouge pour les actions destructrices |
| — | Pour les plugins : `confirmer()` et `demanderTexte()` sont disponibles globalement |


## E4 — ENGRAM

Étape uniquement additive : rien de ce qui existait ne change de comportement.

| Nouveauté | Détail |
|---|---|
| Routes | `/api/engram/formats`, `/inspect`, `/import`, `/sources`, `/oublier` |
| Dossiers créés dans le vault | `Sources/` (notes importées) et `_sources/` (copies, en mode copie) |
| Notes importées | En-tête `prisme_source_*` (empreinte, mode, chemin, extracteur, partie) |
| Ancres de bloc | Chaque passage porte `^p-xxxxxxxx` : c'est là que vit son identifiant |
| Registre | `~/.prisme/engram/engram.json` — reconstructible depuis les notes |
| Interface | Bouton 📥 Sources |

Aucun changement de schéma d'index : rien n'est reconstruit.

## Provenance modifiable

| Avant | Après |
|---|---|
| Provenance posée seulement à la création d'une note générée | Fiche ⓘ modifiable : ajouter, corriger ou retirer des champs sur n'importe quelle note |
| — | `POST /api/provenance` (champs validés) ; `POST /api/provenance/id` renvoie aussi le contenu |
| `GET /api/provenance` : champs de l'index seulement | L'en-tête du fichier fait foi, complété par l'index |
| Badge 🤖 dès qu'un outil était renseigné | 🤖 seulement si un modèle est intervenu ; sinon ⓘ |

Aucun changement de schéma : l'index n'est pas reconstruit.

## E3 — Provenance

| Avant | Après |
|---|---|
| Notes générées sans trace d'origine | En-tête `prisme_*` : identifiant, type, date, outil, modèle, preset, sources |
| `/api/files/save` : `{path, content}` | Accepte `{provenance: {...}}` et renvoie `content` (note estampillée) |
| — | Nouvelles routes `/api/provenance` et `/api/provenance/id` |
| — | Un `prisme_id` est posé sur une note citée par une note générée (écriture limitée à l'en-tête, instantané forcé) |
| Tags : seulement `#tag` dans le corps | Les `tags:` de l'en-tête comptent aussi |
| Index en schéma 1 | Schéma 2 (table `note_meta`) : **l'index se reconstruit tout seul** au premier lancement |
| Plugins : `post('/api/files/save', …)` | `saveGenerated(chemin, contenu, provenance)` côté interface, `ctx.write_note(..., provenance=...)` côté serveur |

L'instantané de `.trash/versions/` était limité à une copie toutes les 5 minutes par
fichier ; une écriture non demandée par l'utilisateur (pose d'identifiant) en fait
toujours une.

## Confort d'édition

| Avant | Après |
|---|---|
| `Ctrl+F` : recherche du navigateur dans la page | Recherche dans la note ouverte (`Ctrl+Maj+F` reste la recherche globale) |
| `Ctrl+Z` : annulation native du navigateur, perdue au changement d'onglet | Historique de PRISME, un par fichier ouvert, 200 pas, en mémoire |
| Éditeur sans repère de position | Gouttière de numéros de ligne et barre d'état « Ligne N, col N » |

Aucun changement de format ni de route.

## E2 — Index SQLite

| Avant | Après |
|---|---|
| Index en mémoire, reconstruit à chaque appel | Index SQLite dans `~/.prisme/index/<empreinte du vault>.db` |
| Recherche par sous-chaîne, sans classement | FTS5 : classement BM25, insensible aux accents, recherche par préfixe (« predi » trouve « prédiction ») |
| Plafond de 5 000 notes (`MAX_SCAN`) | Plus de plafond pour la recherche, les tags, le graphe et les backlinks |
| Graphe et backlinks : relecture de tous les fichiers à chaque appel | Requêtes sur l'index |
| Résultats : extraits bruts, surlignage côté navigateur | Extraits fournis par SQLite, avec titre de section ; le serveur encadre les termes trouvés par `\x01`/`\x02` |
| `/api/search` utilisait le dossier affiché | Cherche dans tout le vault ; le paramètre `dir` reste possible pour limiter à un sous-dossier |
| Tags `#méthode` tronqués à `#m` | Accents acceptés dans les tags ; un tag doit contenir au moins une lettre |
| `[[note]]` pouvait se résoudre vers `manote.md` | Résolution : chemin relatif, puis fin de chemin exacte, puis nom sans extension ; à égalité, le chemin le plus court |
| — | Nouvelles routes `/api/index/status` et `/api/index/rebuild`, état et bouton dans Paramètres |
| — | Nouveau pour les plugins : `ctx.search(texte)` |
| `prisme_core/search_index.py` | Supprimé, remplacé par `prisme_core/index/` |

Toute évolution future des règles d'extraction doit incrémenter `SCHEMA_VERSION`
(`prisme_core/index/store.py`) : l'index existant est alors reconstruit tout seul.

## E1 — API des plugins, gestionnaire, secrets

**Plugins**

| Avant | Après |
|---|---|
| `from second_brain import …` | Supprimé. Un plugin n'importe que `prisme_core.api` |
| `register(app, rd_cfg)` | `register(ctx)` |
| Routes libres (`/api/arxiv/…`) | Routes sous `/api/plugins/<id>/…` |
| Manifest sans `id` ni `api_version` | `id` (= nom du dossier) et `api_version: 1` obligatoires ; sinon le plugin est marqué « incompatible » et ignoré |
| Secrets lus dans `.env` à l'import | `ctx.secret()` : coffre chiffré, puis `.env` en secours |
| Données dans `~/.secondbrain/` | Données dans `~/.prisme/plugins/<id>/` (reprise automatique, une fois, des fichiers V1 des plugins Prompts et RSS) |
| Plugins toujours chargés | Activables et désactivables ; état dans `~/.prisme/plugins.json` |

URLs des six plugins fournis : `/api/arxiv/` → `/api/plugins/arxiv/`, `/api/context/` →
`/api/plugins/context/`, `/api/ddg/` → `/api/plugins/duckduckgo/`, `/api/osintcx/` →
`/api/plugins/osint-cx/`, `/api/prompts/` → `/api/plugins/prompts/`, `/api/rss/` →
`/api/plugins/rss/`. Leur version passe à 2.0.0.

**Cœur**

| Avant | Après |
|---|---|
| Clé d'API en clair dans `config.json` | Chiffrée (DPAPI) sous Windows, `"api_key": "dpapi:…"` ; migration automatique ; hors Windows, en clair et signalé |
| `/api/test` renvoyait le début de la clé | Renvoie seulement l'état de la clé (`key_state`) |
| `/api/config` | Ajoute `key_state` et `key_protected` |
| `/api/files` listait tout le disque | Dans le vault : dossiers et fichiers ; hors du vault : dossiers seulement |
| Paramètre `dir` libre (recherche, tags, graphe, backlinks, synthèse de dossier) | Doit rester dans le vault, sinon 403 |
| `/api/ai/folder` refusait les modèles locaux sans clé | Même règle que les autres appels IA |
| `config.json` lu dans la page de code du système | Lu et écrit en UTF-8 (lecture de secours dans la page de code locale) |
| Renommer en `..` ou vers un nom existant | Refusé |
| `docs/DECISIONS.md` | Une fiche par décision dans `docs/decisions/` |
| Passerelle `second_brain` | Supprimée |

Nouveaux fichiers dans le profil : `plugins.json`, `secrets.json`, `plugins/<id>/`,
`staging/` (archives en attente, effacées après une heure), `corbeille-plugins/`.

## E8 — Découpage du cœur

| Avant (V1) | Après (PRISME) |
|---|---|
| `python second_brain.py` | `python prisme.py` ou `python -m prisme_core` |
| `second_brain.py`, `ui.html` | package `prisme_core/`, interface `prisme_core/web/` |
| Profil `~/.secondbrain/` | Profil `~/.prisme/` ; `config.json` de la V1 est copié au premier lancement s'il existe (la V1 n'est pas modifiée) |
| Vault par défaut `Documents/Second Brain` | `Documents/PRISME` |
| En-tête de session `X-SB-Token` | `X-Prisme-Token` |
| Variable `SECONDBRAIN_NO_AUTH=1` | `PRISME_NO_AUTH=1` |
| CSS et JS des plugins concaténés dans la page | Un fichier servi par plugin : `/plugins/<dossier>/ui.css` et `ui.js` |
| Marqueurs `/* PLUGIN_CSS */`, `/* PLUGIN_JS */` | Marqueurs `<!-- PLUGIN_STYLES -->`, `<!-- PLUGIN_SCRIPTS -->` |
| Scripts `patch_*.py` | Supprimés (déjà appliqués dans la base) |
| Nouveau : `PRISME_DATA_DIR` | Permet d'utiliser un profil isolé (tests, essais) |

Inchangé : les plugins V1 fonctionnent encore via la passerelle `second_brain`,
retirée à l'étape E1.
