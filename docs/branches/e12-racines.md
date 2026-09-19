# E12 — Plusieurs racines de vault

## Objectif

Travailler sur plusieurs dossiers de notes sans changer de vault ni tout réindexer, et
voir réellement ce qu'on s'apprête à choisir. Décision appliquée :
[0028](../decisions/0028-plusieurs-racines-de-vault.md).

## Ce qui change

**Plusieurs racines déclarées.** Dans chacune, tout fonctionne comme dans le vault
actuel : voir, ouvrir, éditer, indexer, chercher. **Hors de ces racines, rien ne
change** — dossiers seulement, aucun nom de fichier, aucune lecture.

La garde n'est pas affaiblie. Elle porte sur une liste au lieu d'un chemin unique : ce
qui était refusé hier l'est encore, sauf ce que tu as explicitement déclaré.

### Les agents ne suivent pas

`safe_path` sert à la fois l'interface, les plugins et `/api/v1/`. Élargir sans
précaution aurait élargi pour tout le monde d'un coup — y compris pour les clés d'agent
livrées en E6.

- Une clé reste bornée à la **racine principale**, quelles que soient les racines
  déclarées.
- Le droit `toutes_racines` s'accorde **clé par clé**, comme le droit d'écriture.
- Hors des racines, même avec ce droit, tout reste refusé.

La restriction est posée **en un seul endroit** — la garde de `/api/v1/` — dans le
contexte de la requête, et `safe_path` l'honore partout, y compris dans les plugins
appelés en cascade. Conséquence voulue : oublier un appel échoue du côté restreint,
jamais du côté permissif.

### Un index par racine, une recherche qui les couvre

Chaque racine garde son index et son magasin de vecteurs — la machinerie existante était
déjà indexée par empreinte de chemin (0010), donc rien à réécrire.

La recherche interroge chaque racine et **fusionne par RRF**. C'est nécessaire, pas
décoratif : des scores BM25 issus d'index différents ne sont pas comparables — une note
d'un petit vault obtiendrait mécaniquement un meilleur score qu'une note équivalente d'un
gros. RRF ne compare que des rangs. C'est déjà ce qui marie lexical et sémantique en E7.

Un résultat porte sa racine, et l'interface l'affiche dès qu'il y en a plusieurs : sans
ça, deux fichiers homonymes dans deux racines seraient indiscernables.

### Ce qui reste borné à une racine

Les `[[liens]]`, les backlinks, le graphe et les tags. Un lien ne traverse pas un vault :
deux racines sont deux ensembles de notes, pas un seul éclaté.

La corbeille et les versions suivent aussi leur racine — un fichier d'une racine
secondaire ne part pas dans le `.trash` d'une autre.

### Refusé à l'ajout

Un dossier inexistant (on ne crée pas un vault sur une faute de frappe), un doublon, et
surtout une **racine imbriquée dans une autre** : un même fichier appartiendrait alors à
deux index. Plafond de huit racines.

## Routes

| Route | Rôle |
|---|---|
| `GET /api/racines` | Les racines, avec leur état et leur nombre de notes |
| `POST /api/racines` | Déclarer une racine supplémentaire |
| `POST /api/racines/retirer` | Cesser de regarder une racine — **aucun fichier n'est touché** |
| `POST /api/racines/principale` | Promouvoir une racine ; l'ancienne reste déclarée |
| `GET /api/files` | Renvoie aussi `racine` et la liste `racines` |
| `GET /api/search` | Couvre toutes les racines ; chaque résultat porte la sienne |
| `GET /api/index/status` | État par racine |
| `POST /api/index/rebuild` | `{"racine": …}` pour une seule, sinon toutes |

## Interface

Une barre de racines dans l'explorateur, qui n'apparaît qu'à partir de deux, avec la
principale marquée. Un `＋` pour déclarer le dossier affiché. Le réglage complet est dans
Paramètres : ajouter, retirer, promouvoir, réindexer.

## Un bug attrapé au passage

Le chemin d'une racine était encodé dans l'attribut `onclick`, puis réencodé par
`loadDir` pour l'URL : double encodage, et le basculement de racine ne marchait pas. Les
tests ne l'avaient pas vu — c'est la vérification navigateur qui l'a montré.

## Fichiers

| Fichier | Rôle |
|---|---|
| `prisme_core/vault.py` | `vault_roots()`, `racines_autorisees()`, `safe_path` multi-racines, `racine_de()` |
| `prisme_core/agents/garde.py` | Bornage des racines par clé, en un seul endroit |
| `prisme_core/agents/cles.py` | Droit `toutes_racines` |
| `prisme_core/routes/racines.py` | Gestion des racines |
| `prisme_core/routes/search.py` | Recherche, tags et index par racine ; fusion RRF |
| `prisme_core/routes/files.py` | Listing qui connaît les racines |
| `prisme_core/web/js/racines.js`, `explorer.js`, `search.js` | Barre de racines, réglage, origine des résultats |
| `tests/test_e12_racines.py` | 28 tests |

## Vérifié

- 288 tests, dont 28 pour cette étape — la majorité portant sur **ce qui reste refusé**.
- Dans le navigateur, avec deux racines réelles et un troisième dossier hors racines :
  bascule entre racines, recherche qui trouve une note de la racine secondaire, réglage
  complet.
- Et par appels directs sur le dossier hors racines : `outside_vault: true`, **aucun nom
  de fichier**, lecture en 403, et le mot qu'il contient introuvable par la recherche.
