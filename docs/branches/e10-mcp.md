# E10 — Adaptateur MCP

## Objectif

Travailler avec Claude Code, ou tout agent qui parle MCP, **dans** le vault — sans écrire
à la main des appels HTTP à chaque session. Décision appliquée :
[0032](../decisions/0032-adaptateur-mcp.md).

## Ce qui change

```
Claude Code ──stdio(MCP)──> mcp/prisme_mcp.py ──HTTP + clé──> PRISME ──> vault
```

### Le cœur ne change pas

Aucun blueprint nouveau, aucune surface HTTP nouvelle, donc aucune surface d'attaque
nouvelle. L'adaptateur est un script à part, lancé par le client MCP, qui rappelle
`/api/v1/` — l'API livrée en E6, conçue stable pour ça.

### L'adaptateur ne fait aucune logique métier

Authentification, droits par clé, bornage aux racines, journal, file de validation :
tout reste dans PRISME, où c'est déjà testé.

C'est la propriété qui compte : **l'adaptateur est jetable**. Le réécrire, le remplacer,
en avoir deux — rien ne change ce qu'un agent a le droit de faire. Un adaptateur qui
referait les contrôles lui-même finirait par diverger, et diverger d'une garde de
sécurité, c'est la perdre. Un test vérifie qu'il n'importe pas `prisme_core`.

### Bibliothèque standard uniquement

Il est lancé par le client MCP avec le Python qu'il trouve, pas par PRISME. Exiger une
dépendance ici, ce serait exiger une installation de la part de quelqu'un qui voulait
seulement coller un bloc de configuration. Un test interdit les imports tiers.

### Droits : ceux d'E6, sans exception

Une clé MCP est une clé d'agent ordinaire : **lecture et proposition**. Ce que l'agent
trouve va dans la file de validation ; rien n'entre dans le vault sans accord. L'écriture
directe s'accorde clé par clé, dans le même onglet et avec la même confirmation.

Il n'y a **pas** de catégorie « clé MCP » dans le trousseau : un régime de droits
parallèle, c'est un endroit de plus où l'on oubliera de reporter une restriction.

### Une route de plus dans `/api/v1/` : l'arbre

`GET /api/v1/arbre` expose la recherche en arbre d'E13, en lecture seule, **sans jamais
appeler de modèle**. Seule extension de la surface d'E6, et elle se justifie par la mesure
d'E13 : sur 29 notes retenues, 12 n'étaient remontées par aucun score. Un agent limité à
la recherche plate paie le même nombre de jetons pour un contexte moins bon, et ne voit
aucune relation entre les notes.

### La configuration est produite par PRISME

Une clé, un chemin absolu, une URL : trois choses à assembler sans se tromper, et l'erreur
ne se voit qu'au refus de démarrage du client. L'onglet « Claude Code (MCP) » de la fenêtre
Agents crée la clé et rend le bloc prêt à coller, chemin en barres obliques — un antislash
dans du JSON doit être échappé, et c'est la faute que tout le monde fait.

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

Les descriptions comptent autant que le code : ce sont elles qui décident si l'agent
choisit le bon outil. `prisme_chercher` et `prisme_arbre` se ressemblent, donc chacune dit
**quand** la prendre — sinon l'agent prend toujours la première. Un test le vérifie.

## Un défaut d'E13 déterré par cette étape

En écrivant les tests d'E10, l'arbre est sorti **vide** sur « calibration Brier », alors
que « calibration » et « Brier » désignaient chacun une note, reliées entre elles.

Cause : **la recherche lexicale exige tous les termes**. Aucune note ne contenait les deux,
donc aucune amorce, donc aucun arbre — dans le cas précis que l'arbre devrait le mieux
servir. Le banc de mesure d'E13 ne pouvait pas le voir : toutes ses notes contenaient tous
les termes.

Correction volontairement étroite : **un repli terme par terme, dans l'arbre seulement**,
et seulement quand la question entière ne rend rien. `/api/search` n'est pas touchée —
changer le sens de la recherche pour toute l'application depuis une étape sur MCP serait
exactement le glissement qu'on évite. Les amorces trouvées ainsi pèsent moitié moins, et
le repli est signalé (`repli_par_terme`) plutôt que silencieux.

## Deux détails corrigés sur la surface des agents

- **Caractères de contrôle** : `/api/v1/recherche` renvoyait les marqueurs de surlignage
  `\x01`/`\x02`, posés pour le navigateur. Un agent y lisait des caractères de contrôle au
  milieu de son texte. Ils sont retirés, sur la seule surface qui sert aux agents.
- **Accents échappés** : sans `ensure_ascii=False`, chaque accent devient `\uXXXX`, six
  caractères au lieu d'un — sur un vault en français, c'est du gaspillage pur.

## Un défaut du code livré : l'encodage des flux

Le second essai a échoué sur les deux seuls tests qui passent par `prisme_arbre`. Cause :
les motifs de l'arbre portent `→` et `←`, et l'adaptateur écrivait sur la sortie standard
avec **l'encodage du système** — `cp1252` sous Windows, qui ne sait pas coder ces flèches.
`sys.stdout.write` levait un `UnicodeEncodeError`, la réponse ne partait jamais, et le
client ne voyait qu'une session muette.

Celui-là n'était pas un défaut de banc : un vrai Claude Code sous Windows aurait rencontré
la même chose dès la première recherche en arbre.

L'adaptateur force désormais l'UTF-8 sur ses trois flux, avec `newline=""` pour que
Windows ne traduise pas `\n` en `\r\n` sous un protocole qui se lit ligne à ligne.
Vérifié en simulant la console Windows (`PYTHONIOENCODING=cp1252`) : sans la correction,
la réponse devient `'charmap' codec can't encode` ; avec, la flèche arrive intacte.

## Deux défauts de banc, révélés par Windows

Le premier essai de livraison a produit huit échecs et deux erreurs chez l'auteur, et
zéro chez moi. Les deux causes étaient dans les tests, pas dans le code livré — et toutes
deux invisibles sous Linux.

**Un environnement fabriqué à la main.** Le banc lançait l'adaptateur avec un
environnement minimal. Sous Windows, un processus Python sans `SystemRoot` ne peut pas
initialiser Winsock : tout appel réseau échoue en `[WinError 10106]`. Les tests
affichaient donc « PRISME ne répond pas » — accusant le code livré. L'environnement est
désormais hérité, et un test vérifie que les variables vitales de la plateforme courante
atteignent bien le sous-processus.

**Un fichier ouvert qu'on croyait pouvoir effacer.** Ces tests laissent tourner un serveur
Flask et des sous-processus. Sous Linux, un fichier ouvert s'efface quand même ; sous
Windows, non — et c'est le nettoyage du test **suivant** qui échouait, E12 tombant sur
`[WinError 32]` à cause d'E10. Trois corrections : E10 travaille maintenant dans son
propre dossier, ses sous-processus sont terminés pour de bon, et les boucles d'effacement
des bancs tolèrent un verrou transitoire.

C'est la deuxième fois que l'écart Linux/Windows mord, après les fins de ligne d'E13. Le
motif est constant : je suppose la sémantique POSIX, elle est fausse chez l'auteur, et les
tests accusent le code.

## Fichiers

| Fichier | Rôle |
|---|---|
| `mcp/prisme_mcp.py` | L'adaptateur : protocole MCP, traduction vers `/api/v1/` |
| `prisme_core/routes/agent_api.py` | Route `/api/v1/arbre`, nettoyage des marqueurs |
| `prisme_core/routes/agents.py` | `POST /api/agents/mcp` : clé + configuration prête à coller |
| `prisme_core/arbre/parcours.py` | Repli par terme quand la question entière ne rend rien |
| `prisme_core/web/index.html`, `js/agents.js`, `css/agents.css` | Onglet « Claude Code (MCP) » |
| `tests/test_e10_mcp.py` | 35 tests |
| `tests/test_e13_arbre.py` | 3 tests de plus, pour le repli ; effacement tolérant |
| `tests/commun.py` | `effacer()` : effacement qui tolère un verrou Windows |
| `tests/test_e12_racines.py` | Effacement tolérant |

## Vérifié

- 359 tests, dont 35 pour cette étape. Le protocole est exercé **en vrai** : sous-processus,
  JSON-RPC sur l'entrée standard. Un test qui appellerait les fonctions en direct ne verrait
  ni les erreurs de flux, ni un `print` égaré dans `stdout` — la panne classique de ce genre
  d'adaptateur.
- La moitié des tests portent sur **ce qui ne doit pas passer** : écriture sans le droit,
  lecture hors vault, écriture hors vault même avec le droit, clé absente, clé révoquée en
  cours de session, PRISME éteint.
- Dans le navigateur : onglet, génération de la configuration, chemin sans antislash, clé
  visible dans le trousseau sans droit d'écriture.

## Ce qui n'est pas fait

L'adaptateur n'a jamais été branché sur un vrai Claude Code. Les tests reproduisent le
protocole fidèlement, mais un client réel a ses exigences propres — c'est la première chose
à essayer.
