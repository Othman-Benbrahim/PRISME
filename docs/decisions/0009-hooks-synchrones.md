# 0009 · Hooks synchrones

- **Statut** : appliquée en E1
- **Écrite** : 2026-09-16

**Retenu.** Les plugins abonnés à un événement s'exécutent avant la confirmation, avec un
délai maximal par hook au-delà duquel le plugin est abandonné et signalé. Les traitements
lourds du cœur (indexation, ingestion) tournent en tâche de fond, hors hooks.

**Risque accepté.** Un plugin lent ralentit la sauvegarde.
