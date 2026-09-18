# Sources IA sur la note ouverte

## Problème

E5 apportait « ✨ Demander à l'IA » dans la fenêtre **Sources citées**. Ce bouton balaie
tout le vault, ou un dossier si on en saisit un — jusqu'à douze appels au modèle. Il n'y
avait aucun moyen de dire *« cherche les sources dans cette note-ci, celle que je suis en
train de lire »*, qui est pourtant le geste le plus naturel quand on vient d'écrire ou
d'importer quelque chose.

## Ce qui change

Un bouton **🔖 Sources IA** dans la barre de l'éditeur, à côté de « 🔗 Liens IA ». Il
analyse la note ouverte, elle seule, en un appel, et ouvre la file de validation sur le
résultat. S'il ne trouve rien, il le dit sans ouvrir de fenêtre.

`POST /api/objets/ia` accepte désormais `{"note": "<chemin>"}` en plus de `dossier`.

Deux garde-fous du balayage automatique ne s'appliquent pas à ce chemin, délibérément :

- **le plafond de notes** (`MAX_NOTES_IA`) n'a pas de sens pour une note unique ;
- **la longueur minimale** (`MIN_CAR_IA`, 120 caractères) sert à ne pas gaspiller un
  appel sur un brouillon pendant un balayage automatique. Demander l'analyse d'une note
  précise est un geste délibéré : on ne refuse pas de l'exécuter parce que la note est
  courte.

Le garde-fou qui compte, lui, reste en place : toute proposition doit citer un extrait
littéral retrouvé dans la note, sinon elle est écartée sans être montrée.

Une note du dossier `Objets/Sources` est refusée — analyser un objet Source à la
recherche de sources n'aurait aucun sens.

## Fichiers

| Fichier | Rôle |
|---|---|
| `prisme_core/objets/balayage.py` | `proposer_par_ia(note=…)` et `_a_examiner()` |
| `prisme_core/routes/objets.py` | `/api/objets/ia` accepte `note` |
| `prisme_core/web/js/objets.js` | `objSourcesDeLaNote()` |
| `prisme_core/web/index.html` | bouton `#ed-src-ia` |
| `tests/test_e5_objets.py` | 4 tests de plus |

## Vérifié

- 203 tests (`python -m unittest discover -s tests`).
- Dans le navigateur, avec un modèle simulé : un clic sur une note citant une source en
  clair, un seul appel, la proposition apparaît dans la file au nom de l'IA.
