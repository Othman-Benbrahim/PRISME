# E1 — API des plugins, gestionnaire, secrets chiffrés

## Objectif

Donner aux plugins un contrat public et versionné, permettre de les installer et de les
désactiver sans redémarrer, chiffrer les clés au repos, et corriger les défauts de garde
hérités de la V1. Décisions appliquées : [0006](../decisions/0006-api-des-plugins-rupture-nette.md),
[0007](../decisions/0007-gestionnaire-de-plugins.md), [0008](../decisions/0008-source-des-plugins.md),
[0009](../decisions/0009-hooks-synchrones.md), [0023](../decisions/0023-cles-et-secrets-chiffres-dpapi.md).

## Ce qui change

- **`prisme_core.api`** : un plugin reçoit un `PluginContext` dans `register(ctx)`.
  Routes, appel IA, accès au vault gardé, dossier de données, secrets, hooks.
  Guide complet : `PLUGIN-DEVELOPMENT.md`.
- **Aiguilleur de routes** : les routes des plugins ne sont pas enregistrées dans Flask,
  qui interdit d'en ajouter après le premier appel. Un point d'entrée unique
  `/api/plugins/<id>/…` les résout. D'où l'installation et l'activation à chaud.
- **Hooks synchrones** (`note_saved`, `note_created`, `note_renamed`, `note_deleted`),
  3 secondes par hook ; un dépassement ou une exception est signalé à l'utilisateur
  sans bloquer la sauvegarde. Un plugin ne reçoit pas ses propres écritures.
- **Gestionnaire de plugins** (bouton 🧩 Plugins) : liste avec statut, activation,
  désinstallation vers `~/.prisme/corbeille-plugins/`, saisie des secrets, installation
  par fichier ZIP ou adresse `https://` après un écran de confirmation (manifest,
  permissions, empreinte SHA-256, liste des fichiers).
- **Vérification des archives** : taille (20 Mo / 100 Mo), nombre de fichiers, chemins
  remontants ou absolus, liens symboliques, manifest valide ; nouvelle vérification au
  moment d'installer ; extraction dans un dossier temporaire puis renommage.
- **Empreinte du dossier installé** mémorisée : un plugin modifié après coup est signalé.
- **Clé d'API chiffrée** (DPAPI, Windows) avec migration automatique ; état affiché
  dans Paramètres ; jamais renvoyée au navigateur.
- **Coffre des secrets de plugins** (`~/.prisme/secrets.json`), lu par `ctx.secret()`
  avant les variables d'environnement.
- **Six plugins migrés** (version 2.0.0) : routes, appels IA, gardes de chemin (Context),
  données dans `~/.prisme/plugins/<id>/` avec reprise des fichiers V1 (Prompts, RSS),
  secrets du coffre (OSINT). Leurs boutons de diagnostic fonctionnent à nouveau : ils
  ouvraient un onglet sans jeton, donc une erreur 403, depuis le durcissement de la V1.
- **Gardes du vault** : `/api/files` hors du vault ne liste que des dossiers ; le
  paramètre `dir` des routes de recherche, tags, graphe, backlinks et synthèse doit rester
  dans le vault ; renommage en `..` refusé ; `config.json` en UTF-8.
- **Décisions** : `docs/DECISIONS.md` devient `docs/decisions/`, une fiche par décision,
  avec trois nouvelles fiches (0021 entrée directe des imports en masse, 0022 horloges,
  0023 DPAPI) et une révision de 0017.

## Fichiers touchés

**Créés** : `prisme_core/api.py`, `hooks.py`, `secrets.py`, `plugin_install.py`,
`routes/plugin_manager.py`, `web/js/plugin-manager.js`, `web/css/plugin-manager.css`,
`tests/commun.py`, `tests/test_e1_plugins.py`, `docs/decisions/` (24 fichiers), ce fichier.

**Modifiés** : `prisme_core/app.py`, `config.py`, `plugins.py`, `vault.py`,
`routes/ai.py`, `files.py`, `pages.py`, `search.py`, `setup.py`, `web/index.html`,
`web/js/helpers.js`, `editor.js`, `settings.js`, les six plugins, `packaging/PRISME.spec`,
`tests/test_e8_structure.py`, `PLUGIN-DEVELOPMENT.md`, `README.md`, `docs/ARCHITECTURE.md`,
`docs/RUPTURES.md`, `docs/FEUILLE-DE-ROUTE.md`.

**Supprimés** : `prisme_core/compat.py`, `docs/DECISIONS.md`.

## Ruptures

Voir la section E1 de `docs/RUPTURES.md`. En résumé : tout plugin V1 est désormais
« incompatible » tant qu'il n'est pas migré, et les URLs des plugins fournis changent.

## Tester

```powershell
python -m unittest discover -s tests -v
python prisme.py
```

34 tests passent sous Linux ; le 35e (`test_dpapi_reel`) ne s'exécute que sous Windows et
vérifie le vrai chiffrement. **C'est sa première exécution réelle.**

Vérifications manuelles :

1. Paramètres : la clé doit apparaître « chiffrée sur cette machine » ; `~/.prisme/config.json`
   doit contenir `dpapi:` et plus la clé en clair.
2. 🧩 Plugins : les six plugins sont « Actif » ; désactiver RSS puis recharger la page
   fait disparaître son bouton ; le réactiver le fait revenir.
3. OSINT : enregistrer un secret, vérifier qu'il s'affiche « défini (chiffré) » et que
   `~/.prisme/secrets.json` ne le contient pas en clair.
4. Prompts : vos presets V1 doivent être présents (repris de `~/.secondbrain/`).
5. Ouvrir chaque plugin depuis la barre d'outils et lancer une action simple.

Vérifié ici dans un navigateur réel (Chromium) : aucun message d'erreur JavaScript ni
réponse HTTP en échec ; modales des plugins alimentées par les nouvelles routes ;
installation d'un plugin ZIP à chaud, bouton visible après rechargement et route
fonctionnelle ; désactivation de RSS ; saisie d'un secret ; reprise des presets V1 ;
sauvegarde d'une note. Exe reconstruit sous Linux : les plugins se chargent.

## Limites connues

- Les permissions informent l'utilisateur mais ne confinent pas le code d'un plugin.
- Un hook qui dépasse son délai continue en arrière-plan : Python ne sait pas
  l'interrompre.
- Mettre à jour un plugin déjà chargé demande un redémarrage.
- Désinstaller un plugin chargé le coupe tout de suite, mais son code reste en mémoire
  jusqu'au redémarrage.
- Hors Windows, clés et secrets restent en clair (et l'interface le dit).
- Les plugins RSS et Context écrivent ou lisent encore le vault directement, sans passer
  par `ctx.write_note` : leurs écritures ne déclenchent pas de hook.

## Hors périmètre

Index SQLite (E2), provenance et horloge d'enregistrement (E3).
