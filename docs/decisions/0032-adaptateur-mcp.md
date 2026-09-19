# 0032 · Adaptateur MCP

- **Statut** : acceptée, appliquée (E10)
- **Écrite** : 2026-09-19

## Problème

[0018](0018-acces-des-agents.md) avait écarté MCP au profit d'une API HTTP à clés, jugée
plus simple et plus contrôlable. Le besoin est revenu autrement : pouvoir travailler avec
Claude Code ou un agent autonome **dans** le vault, sans écrire à la main des appels HTTP
à chaque session.

L'API d'E6 existe, elle est testée, et elle a été conçue stable pour ça. Il ne manque
qu'une traduction.

## Décision

**Un serveur MCP en entrée/sortie standard, qui rappelle `/api/v1/` en HTTP local.**

```
Claude Code ──stdio(MCP)──> mcp/prisme_mcp.py ──HTTP+clé──> PRISME ──> vault
```

### L'adaptateur ne fait aucune logique métier

Authentification, droits par clé, bornage aux racines, journal, file de validation :
tout reste dans PRISME, où c'est déjà testé. L'adaptateur traduit des noms d'outils en
chemins d'URL, et des réponses JSON en texte.

C'est la propriété qui compte : **l'adaptateur est jetable**. Le réécrire, le remplacer
par un autre langage, en avoir deux — rien de tout cela ne change ce qu'un agent a le
droit de faire. Un adaptateur qui referait les contrôles lui-même finirait par diverger,
et diverger d'une garde de sécurité, c'est la perdre.

### stdio, pas HTTP

C'est le transport que les clients MCP attendent par défaut, et la configuration se
réduit à un bloc JSON. Le cœur ne change pas d'un octet : aucun blueprint, aucune
surface HTTP nouvelle, donc aucune surface d'attaque nouvelle.

Contrepartie assumée : PRISME doit tourner. L'adaptateur le dit en clair quand ce n'est
pas le cas, au lieu d'échouer silencieusement.

### Bibliothèque standard uniquement

L'adaptateur est lancé par le client MCP, avec le Python qu'il trouve — pas par PRISME.
Exiger une dépendance ici, ce serait exiger une installation de la part de quelqu'un qui
voulait seulement coller un bloc de configuration.

### Droits : ceux d'E6, sans exception

Une clé MCP est une clé d'agent ordinaire : **lecture et proposition** par défaut. Ce
qu'un agent trouve va dans la file de validation ; rien n'entre dans le vault sans accord.
L'écriture directe s'accorde clé par clé, dans le même onglet que les autres, avec la même
confirmation.

Il n'y a **pas** de catégorie « clé MCP » dans le trousseau. Créer un régime de droits
parallèle, c'est créer un endroit où l'on oubliera de reporter une restriction.

### Une route de plus dans `/api/v1/` : l'arbre

`GET /api/v1/arbre` expose la recherche en arbre d'E13, en lecture seule, **sans jamais
appeler de modèle**. C'est la seule extension de la surface d'E6.

Elle se justifie par la mesure d'E13 : sur 29 notes retenues, 12 n'étaient remontées par
aucun score. Un agent limité à la recherche plate paie le même nombre de jetons pour un
contexte moins bon, et ne voit aucune relation entre les notes.

### La configuration est produite par PRISME

Une clé, un chemin absolu, une URL : trois choses à assembler sans se tromper, et
l'erreur ne se voit qu'au refus de démarrage du client. L'onglet « Claude Code (MCP) »
crée la clé et rend le bloc prêt à coller, chemin en barres obliques — un antislash dans
du JSON doit être échappé, et c'est la faute que tout le monde fait.

## Les outils exposés

| Outil | Droit | Route |
|---|---|---|
| `prisme_notes` | lecture | `GET /api/v1/notes` |
| `prisme_lire` | lecture | `GET /api/v1/note` |
| `prisme_chercher` | lecture | `GET /api/v1/recherche` |
| `prisme_arbre` | lecture | `GET /api/v1/arbre` |
| `prisme_sources` | lecture | `GET /api/v1/objets` |
| `prisme_proposer` | proposition | `POST /api/v1/proposer` |
| `prisme_ma_file` | proposition | `GET /api/v1/file` |
| `prisme_ecrire` | **ecriture** | `POST /api/v1/note` |

Les descriptions d'outils comptent autant que le code : c'est elles qui décident si
l'agent choisit le bon. `prisme_chercher` et `prisme_arbre` se ressemblent, donc chacune
dit **quand** la prendre — sinon l'agent prend toujours la première.

## Écarté

- **PRISME sert MCP lui-même en HTTP** : rien à lancer, mais tous les clients ne gèrent
  pas ce transport aussi bien que stdio, et l'authentification par en-tête se configure
  moins simplement. À reconsidérer si un client le réclame.
- **Les deux transports** : double surface à maintenir et à tester, pour un usage qui
  n'en demandera peut-être qu'une.
- **Lecture seule par défaut** : plus sûr, mais l'agent ne pourrait alors rien apporter —
  ce qui retire l'essentiel de l'intérêt.
- **Écriture directe par défaut** : la provenance deviendrait le seul filet.
- **Exposer les routes d'écriture de fichiers de l'interface** (`/api/files/…`) : elles
  n'ont pas été conçues pour un appelant non humain, et n'ont pas la garde des agents.
