# 0012 · Identifiants posés au besoin

- **Statut** : acceptée, non encore appliquée
- **Écrite** : 2026-09-16

**Retenu.** Une note humaine ne reçoit `prisme_id` que lorsque quelque chose y fait
référence. Les notes produites par une machine en ont un dès leur création. Identifiant
stable (UUID court) plutôt que chemin.

**Détails.** La pose se limite au frontmatter, après un instantané. Une référence encore
fondée sur un chemin devient « orpheline » si la note est renommée hors de PRISME ; le
rattachement par contenu identique est proposé, jamais deviné.
