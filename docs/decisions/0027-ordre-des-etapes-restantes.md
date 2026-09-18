# 0027 · Découpage et ordre des étapes restantes

- **Statut** : acceptée
- **Écrite** : 2026-09-19

## Décision

Deux chantiers étaient reportés sans étape : l'adaptateur MCP ([0018](0018-acces-des-agents.md))
et les types d'objets autres que Source ([0017](0017-objets-conceptuels.md)). Ils
deviennent **E10** et **E11**, séparément, et passent **avant** la publication (E9).

| Étape | Objet | Pourquoi là |
|---|---|---|
| **E7** | Embeddings | Dernière brique de recherche ; indépendante du reste |
| **E10** | Adaptateur MCP | Mince : une traduction au-dessus de `/api/v1/`, qui existe déjà et a été conçue stable pour ça |
| **E11** | Types d'objets et leur paramétrage | Le plus gros morceau restant ; se fera type par type |
| **E9** | Publication | En dernier : elle sert aux autres, pas à l'auteur |

## Pourquoi séparer E10 et E11

Les réunir ferait attendre le gros pour obtenir le petit. L'adaptateur MCP est une couche
de traduction sans fonctionnalité nouvelle ; les types d'objets sont plusieurs semaines de
travail. Le premier change l'usage quotidien tout de suite.

## Pourquoi E9 en dernier

E9 — import d'un vault V1, guide de passage, première version publique — profite à des
utilisateurs qui n'existent pas encore. E10 et E11 profitent à l'auteur immédiatement. Et
un PRISME qui sort avec MCP et les types d'objets est une meilleure proposition qu'un
PRISME qui sort sans.

## Points de conception notés pour E10

- **Les droits par clé d'E6 suffisent, à condition de s'en servir.** Un agent de codage
  veut écrire ; un agent de veille ne devrait que proposer. Deux clés, deux droits, pas
  une clé commode pour les deux.
- **Un serveur MCP doit être joignable.** PRISME est une application qu'on ouvre. À
  trancher : l'adaptateur le lance s'il ne tourne pas, ou il refuse proprement en le
  disant.
