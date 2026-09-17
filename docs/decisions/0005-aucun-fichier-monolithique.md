# 0005 · Aucun fichier monolithique

- **Statut** : appliquée en E8
- **Écrite** : 2026-09-16

**Retenu.** Le cœur Python est un package de modules courts ; l'interface est découpée
en fichiers CSS et JS par zone ; chaque plugin est chargé comme fichier distinct.

**Pourquoi.** Ne pas tout mettre dans le même panier : une erreur dans un fichier ne doit
faire tomber que sa propre fonctionnalité.
