# Ruptures par rapport à la base V1

Journal cumulatif des changements incompatibles avec Second Brain V1 (`base-v1`).
Chaque étape ajoute sa section. Ce fichier servira de base au guide de passage.

<!-- Les étapes ajoutent leurs sections ci-dessous, la plus récente en haut. -->

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
