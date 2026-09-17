# 0018 · Accès des agents

- **Statut** : acceptée, non encore appliquée
- **Écrite** : 2026-09-16

**Retenu.** API HTTP locale (`127.0.0.1`) avec une clé par agent : affichée une seule fois,
seule son empreinte est stockée, révocable, journalisée. Droits par défaut : lecture et
proposition dans la file. Écriture directe seulement sur accord explicite, clé par clé.
Plafond de propositions en attente par clé.

**Reporté.** Adaptateur MCP au-dessus de la même API.

**Écarté.** CLI dédiée.
