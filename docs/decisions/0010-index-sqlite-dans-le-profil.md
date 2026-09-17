# 0010 · Index SQLite dans le profil

- **Statut** : acceptée, non encore appliquée
- **Écrite** : 2026-09-16

**Retenu.** `~/.prisme/index/<empreinte du chemin du vault>.db`, avec un fichier de
correspondance empreinte → chemin.

**Pourquoi.** Aucun risque de corruption par un service de synchronisation ; l'index se
reconstruit toujours depuis les `.md`.

**Écarté.** Base dans le vault.
