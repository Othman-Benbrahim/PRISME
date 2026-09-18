# 0018 · Accès des agents

- **Statut** : appliquée en E6 ; l'adaptateur MCP reste reporté
- **Écrite** : 2026-09-16

**Retenu.** API HTTP locale (`127.0.0.1`) avec une clé par agent : affichée une seule fois,
seule son empreinte est stockée, révocable, journalisée. Droits par défaut : lecture et
proposition dans la file. Écriture directe seulement sur accord explicite, clé par clé.
Plafond de propositions en attente par clé.

**Reporté.** Adaptateur MCP au-dessus de la même API.

**Écarté.** CLI dédiée.

## Application en E6

Surface `/api/v1/`, authentifiée par clé et **jamais** par le jeton de session du
navigateur : les deux portes sont étanches dans les deux sens. `PRISME_NO_AUTH` ne
l'ouvre pas non plus.

La clé sort en clair une seule fois ; seule son empreinte SHA-256 est conservée, avec un
indice pour la reconnaître dans la liste. Droits `lecture` et `proposition` par défaut,
`ecriture` accordée clé par clé derrière une confirmation explicite. Les notes écrites
par un agent sont estampillées à son nom, et chaque écrasement garde une version.

Le plafond de propositions en attente est celui d'E5, appliqué à l'origine
`agent:<nom>` : il devient donc un plafond par clé. Le journal (`journal.jsonl`) consigne
tout appel, y compris les refus et les clés inconnues, et survit à la révocation comme à
l'oubli de la clé.
