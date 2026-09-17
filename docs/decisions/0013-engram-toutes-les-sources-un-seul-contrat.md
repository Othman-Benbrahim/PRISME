# 0013 · ENGRAM : toutes les sources, un seul contrat

- **Statut** : acceptée, non encore appliquée
- **Écrite** : 2026-09-16

**Retenu.** Exports ChatGPT et Claude, Markdown, texte, HTML, dépôts, PDF, DOCX, EPUB,
images. Un contrat d'extraction commun (inspiré de Studio Littéraire) : vérification du
fichier, SHA-256 avant et après extraction, enregistrement du moteur, de sa version et de
sa configuration.

**Répartition.** Formats légers : plugins en Python pur. Formats lourds : plugin qui pilote
un outil externe dans son propre environnement.
