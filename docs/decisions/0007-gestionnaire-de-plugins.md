# 0007 · Gestionnaire de plugins

- **Statut** : appliquée en E1
- **Écrite** : 2026-09-16

**Retenu.** Installer, activer, désactiver, désinstaller depuis l'interface, comme les
extensions d'un navigateur. Le cœur fonctionne sans aucun plugin ; poser un dossier à la
main dans `plugins/` reste possible.

**Détails.** Chaque plugin a son préfixe de routes (`/api/plugins/<id>/`). Désactiver
bloque ses routes et son interface sans redémarrage ; désinstaller envoie son dossier à la
corbeille ; une mise à jour demande un redémarrage. Le manifest déclare `api_version` et
les permissions ; ces permissions **informent** l'utilisateur mais ne confinent pas le
code (Python ne sait pas isoler un plugin).
