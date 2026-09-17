# 0008 · Source des plugins

- **Statut** : appliquée en E1
- **Écrite** : 2026-09-16

**Retenu.** ZIP local ou URL HTTPS.

**Garde-fous.** HTTPS uniquement, taille maximale, refus des chemins `../` et absolus dans
l'archive, écran de confirmation (source, manifest, permissions), empreinte SHA-256
mémorisée, URL d'origine conservée.

**Écarté.** Catalogue centralisé (responsabilité éditoriale).
