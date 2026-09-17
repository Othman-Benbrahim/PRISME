# 0002 · Nom et préfixes

- **Statut** : appliquée en E8 (nom, profil, en-tête) et E1 (API)
- **Écrite** : 2026-09-16

**Retenu.** Dépôt `PRISME`, package `prisme_core`, API des plugins `prisme_core.api`,
profil `~/.prisme/`, champs de frontmatter préfixés `prisme_`, exécutable `PRISME.exe`,
en-tête des clés d'agents `X-Prisme-Key`.

**Pourquoi.** Un paquet `prisme` existe déjà sur PyPI : `prisme_core` évite tout conflit
d'import. Le préfixe `prisme_` reste lisible dans Obsidian sans connaître le projet.

**Écarté.** Préfixe court `pm_` (opaque) ; bloc YAML imbriqué `prisme:` (mal affiché
par le panneau Propriétés d'Obsidian).
