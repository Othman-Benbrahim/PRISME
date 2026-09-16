# E8 — Découpage du cœur

## Objectif

Remplacer les deux fichiers monolithiques de la base V1 (`second_brain.py`, 46 Ko, et
`ui.html`, 86 Ko) par un package de modules courts et une interface découpée par zone,
**sans changer le comportement**. Renommer l'application en PRISME. Supprimer les scripts
`patch_*.py`, déjà appliqués dans la base.

Le découpage a été fait par extraction mécanique (fonctions Python déplacées telles quelles,
plages de lignes pour l'interface), pas par réécriture. Seul le code d'assemblage des
plugins a été réécrit.

## Fichiers touchés

**Créés**
- `prisme.py` : lanceur
- `prisme_core/` : package (voir `docs/ARCHITECTURE.md`)
- `prisme_core/web/` : `index.html`, `css/` (2 fichiers), `js/` (19 fichiers)
- `packaging/PRISME.spec` : construction de l'exe
- `tests/test_e8_structure.py` : 11 tests
- `docs/ARCHITECTURE.md`, ce fichier

**Modifiés**
- `README.md` : lancement
- `requirements.txt` : en-tête, mention de PyInstaller
- `PLUGIN-DEVELOPMENT.md` : avertissement provisoire en tête
- `docs/RUPTURES.md`, `docs/FEUILLE-DE-ROUTE.md`

**Supprimés**
- `second_brain.py`, `ui.html`
- `patch_hardening.py`, `patch_onboarding.py`, `patch_providers.py`,
  `patch_settings.py`, `patch_streaming.py`, `patch_vault.py`

## Changements de comportement

Deux changements, tous deux voulus :

1. **Chaque plugin est chargé séparément.** Son `ui.css` et son `ui.js` sont servis par
   `/plugins/<dossier>/ui.css|ui.js` au lieu d'être concaténés dans la page. Une erreur
   de syntaxe dans un plugin ne bloque plus le reste de l'interface (vérifié avec un
   plugin volontairement cassé : l'erreur reste confinée, les six autres plugins et le
   cœur fonctionnent). Seuls les plugins effectivement chargés sont servis, et seulement
   ces deux fichiers.
2. **Correction d'un défaut de la base.** En V1, le script du jeton était placé en fin de
   page : le premier appel `/api/config` partait sans jeton et recevait une erreur 403.
   `token.js` est maintenant chargé en premier ; l'erreur a disparu.

Pour le reste, l'interface a été comparée dans un navigateur réel (Chromium) entre la base
V1 et cette branche, sur le même vault de test : explorateur, onglets, aperçu Markdown,
carte mentale, backlinks, recherche, tags, graphe, paramètres, ouverture des six plugins,
sauvegarde. Résultats identiques, en dehors des deux points ci-dessus.

## Ruptures

Voir la section E8 de `docs/RUPTURES.md`.

## Tester

```powershell
python -m unittest discover -s tests -v
python prisme.py
```

Vérifications manuelles : ouvrir une note, la modifier, `Ctrl+S`, ouvrir le graphe,
lancer une recherche, ouvrir chaque plugin depuis la barre d'outils.

Construction de l'exe (facultatif) :

```powershell
pip install pyinstaller
pyinstaller packaging/PRISME.spec
```

La spec embarque les modules de la bibliothèque standard utilisés par les plugins
(`xml`, `concurrent`, `urllib`…) : sans eux, les plugins ArXiv et RSS ne se chargent pas
depuis l'exe. Vérifié sous Linux ; à confirmer sous Windows.

## Défauts hérités repérés, non corrigés ici

L'étape se limite au découpage. Ces points sont notés pour les étapes suivantes :

- `/api/files` liste n'importe quel dossier, sans passer par la garde du vault (E1).
- `/api/ai/folder` lit un dossier sans garde de chemin et refuse les fournisseurs locaux
  sans clé, contrairement aux autres routes IA (E1).
- `config.json` est lu et écrit sans encodage explicite : sous Windows, un chemin accentué
  dépend de la page de code locale (E1).
- Les plugins Prompts et RSS stockent encore leurs données dans `~/.secondbrain/` (E1).

## Hors périmètre

Nouvelle API des plugins, gestionnaire de plugins, index SQLite : étapes E1 et E2.
