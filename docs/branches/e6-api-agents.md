# E6 — API locale à clés pour les agents

## Objectif

Permettre à un programme extérieur — un agent, un script, un autre outil — de lire ton
vault et de te proposer des choses, **sans jamais rien y écrire de son propre chef**.
Décision appliquée : [0018](../decisions/0018-acces-des-agents.md), en s'appuyant sur la
file de validation d'E5.

## Ce qui change

### Une surface séparée : `/api/v1/`

Deux portes distinctes, deux authentifications :

| Porte | Qui passe | Comment |
|---|---|---|
| `/api/…` | ton navigateur | jeton de session `X-Prisme-Token` |
| `/api/v1/…` | les agents | clé d'agent `X-Prisme-Cle` ou `Authorization: Bearer` |

Le jeton du navigateur **ne donne pas** accès à `/api/v1/`, et réciproquement. Sans
cette séparation, une page ouverte dans PRISME vaudrait une clé d'agent.

La garde sur l'en-tête `Host` continue de s'appliquer en amont : l'API n'est joignable
que depuis la machine. Et `PRISME_NO_AUTH=1`, qui dispense du jeton de session pendant
un essai, **ne désarme pas** l'authentification des agents — sinon un confort de
développement deviendrait un trou béant.

### Une clé par agent, affichée une seule fois

À la création, la clé en clair sort de PRISME **une fois**. Ensuite, seule son empreinte
SHA-256 est conservée : voler le fichier de profil ne donne aucune clé utilisable. La
liste n'affiche qu'un indice (`prisme-m1CQ…uc`) pour reconnaître laquelle est laquelle.

Pas de KDF lent sur l'empreinte, et c'est délibéré : la clé fait 256 bits d'aléa, elle
n'est ni devinable ni attaquable par dictionnaire. Un PBKDF2 à chaque requête ne
protégerait de rien et coûterait une latence à chaque appel.

### Trois droits, dont un qui ne s'accorde jamais tout seul

| Droit | Par défaut | Ce qu'il ouvre |
|---|---|---|
| `lecture` | ✅ toujours | lister et lire les notes, chercher, lister les objets Source |
| `proposition` | ✅ | déposer dans la file de validation d'E5 |
| `ecriture` | ❌ | écrire une note directement dans le vault |

L'écriture directe se donne clé par clé, depuis l'interface, derrière une confirmation
explicite — et se retire à tout moment. Les notes qu'un agent écrit sont estampillées
`prisme_outil: agent`, `prisme_genere_par: <nom>`, `prisme_agent_cle: <id>` : une note
produite par une machine n'est jamais indiscernable d'une note écrite à la main. Chaque
écrasement garde une version précédente dans `.trash/versions/`.

### Rien n'entre dans le vault sans ton accord

Une proposition d'agent va dans la file de validation, **même quand sa référence est
parfaitement vérifiable**. C'est un point explicite de la décision 0021 : les
propositions d'agents ne bénéficient jamais de l'entrée directe, contrairement au
balayage mécanique que tu déclenches toi-même.

L'étiquette d'origine est `agent:<nom>`, ce qui transforme le plafond par origine d'E5
en **plafond par clé** : un agent emballé ne peut pas noyer la file des autres. Un agent
peut relire ce qu'il a déposé (`GET /api/v1/file`), mais pas la file des autres.

### Un journal que la révocation n'efface pas

Un agent agit sans que tu le regardes : ce que tu peux relire après coup est la seule
garantie qui reste. Chaque appel — accepté ou refusé, y compris avec une clé inconnue —
laisse une ligne dans `~/.prisme/agents/journal.jsonl` : quand, quelle clé, quel appel,
quel statut. Le journal survit à la révocation **et** à l'oubli de la clé : effacer une
clé n'efface pas ce qu'elle a fait. Format JSONL, borné à 5 000 lignes avec rotation ;
une ligne corrompue n'emporte pas le fichier.

## La surface

```
GET  /api/v1/ping        qui suis-je, que puis-je faire     lecture
GET  /api/v1/notes       lister les notes du vault          lecture
GET  /api/v1/note?path=  lire une note + sa provenance      lecture
GET  /api/v1/recherche?q= chercher (index FTS5 d'E2)        lecture
GET  /api/v1/objets      lister les objets Source d'E5      lecture
GET  /api/v1/file        ce que CET agent a déposé          proposition
POST /api/v1/proposer    déposer dans la file de validation proposition
POST /api/v1/note        écrire une note                    ecriture
```

Exemple :

```bash
curl -H "X-Prisme-Cle: prisme-…" http://127.0.0.1:5000/api/v1/ping

curl -X POST -H "X-Prisme-Cle: prisme-…" -H "Content-Type: application/json" \
  -d '{"titre":"Rapport Kybernetica","note":"Veille.md","motif":"cité en clair"}' \
  http://127.0.0.1:5000/api/v1/proposer
```

`GET /api/v1/ping` décrit la surface : un agent peut découvrir ce qu'il a le droit de
faire sans documentation externe.

## Routes de gestion (interface)

`GET /api/agents/cles`, `POST /api/agents/cles`, `/cles/droits`, `/cles/revoquer`,
`/cles/oublier`, `GET /api/agents/journal`. Protégées par le jeton de session, comme le
reste de l'interface.

Un bouton **🔑 Agents** dans l'en-tête ouvre une fenêtre à deux onglets : *Clés d'accès*
et *Journal*.

## Correctif d'interface, hors périmètre mais bloquant

`#mdialog` partageait le `z-index` des autres fenêtres et vient plus tôt dans le DOM :
la fenêtre qui ouvrait une confirmation interceptait les clics, et le bouton était
visible mais inerte. Conséquence, livrée depuis `dialogues-interface` : **« Oublier une
source » dans ENGRAM et « Annuler ce lot » dans E5 ne pouvaient pas être confirmés.**
Corrigé (`#mdialog{z-index:120}`), avec un test qui compare les deux valeurs.

## Fichiers

| Fichier | Rôle |
|---|---|
| `prisme_core/agents/cles.py` | Trousseau : création, empreinte, droits, révocation |
| `prisme_core/agents/garde.py` | Authentification par clé, décorateur `exige(droit)` |
| `prisme_core/agents/journal.py` | Journal JSONL borné, lecture et filtrage |
| `prisme_core/routes/agent_api.py` | La surface `/api/v1/` |
| `prisme_core/routes/agents.py` | Gestion du trousseau depuis l'interface |
| `prisme_core/routes/security.py` | Aiguillage de `/api/v1/` vers la garde par clé |
| `prisme_core/web/js/agents.js`, `css/agents.css` | Fenêtre 🔑 Agents |
| `tests/test_e6_agents.py` | 44 tests |

## Ce qui reste reporté

L'adaptateur MCP au-dessus de la même API (0018). La surface HTTP est volontairement
stable et découvrable pour qu'il puisse se poser dessus sans rien changer au cœur.

## Vérifié

- 199 tests (`python -m unittest discover -s tests`), dont 44 pour cette étape.
- Parcours complet dans le navigateur : création d'une clé, affichage unique, octroi de
  l'écriture derrière confirmation, révocation, journal.
- Appels réels en HTTP avec `curl` depuis l'extérieur de PRISME : `ping`, `recherche`,
  `proposer` — la proposition apparaît bien dans la file de validation d'E5, étiquetée
  au nom de l'agent, en attente de validation.
