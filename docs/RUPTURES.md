# Ruptures par rapport à la base V1

Journal cumulatif des changements incompatibles avec Second Brain V1 (`base-v1`).
Chaque étape ajoute sa section. Ce fichier servira de base au guide de passage.

<!-- Les étapes ajoutent leurs sections ci-dessous, la plus récente en haut. -->

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
