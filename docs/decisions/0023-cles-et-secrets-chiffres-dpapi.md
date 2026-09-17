# 0023 · Clés et secrets chiffrés (DPAPI)

- **Statut** : appliquée en E1
- **Écrite** : 2026-09-17

## Problème

Second Brain V1 stockait la clé d'API en clair dans `config.json` ; les clés des plugins vivaient en clair dans des fichiers `.env`.

## Décision

- Sous Windows, la clé d'API et les secrets déclarés par les plugins sont chiffrés avec DPAPI, pour la session Windows courante, via `ctypes` (bibliothèque standard). Format stocké : `dpapi:<base64>`.
- Une clé en clair est chiffrée automatiquement à sa première lecture.
- Une valeur indéchiffrable (autre machine, autre compte, Windows réinstallé) est traitée comme absente et signalée : « clé illisible sur cette machine ».
- La clé déchiffrée n'est jamais renvoyée au navigateur. La route de diagnostic ne montre plus son début.
- Les plugins lisent leurs secrets par `ctx.secret(nom)` : coffre chiffré `~/.prisme/secrets.json`, puis variable d'environnement (`.env`) en secours. Les secrets se saisissent dans le gestionnaire de plugins.
- Hors Windows, les valeurs restent en clair et l'interface le dit. PRISME ne prétend jamais chiffrer quand il ne le fait pas.

## Limites assumées

- Tout programme lancé sous la même session Windows peut déchiffrer.
- Changer de machine oblige à ressaisir les clés.
- Second Brain V1 n'est pas modifié : son `config.json` garde l'ancienne clé en clair tant que l'utilisateur ne le supprime pas.

## Écarté

- Laisser les clés en clair jusqu'à la publication.
