# E5 — File de validation et objet Source

## Objectif

Faire exister, dans le vault, le **registre des références citées** : ce que tes notes
mentionnent comme source, rassemblé en objets dédoublonnés, avec la distinction entre
ce qui est seulement cité et ce qui a réellement été lu et importé par ENGRAM.

Décisions appliquées : [0017](../decisions/0017-objets-conceptuels.md),
[0021](../decisions/0021-entree-directe-des-imports-en-masse.md),
[0022](../decisions/0022-horloges-des-objets.md).

## Ce qui change

### Un objet Source est une note du vault

Pas une ligne de base : un `.md` dans `Objets/Sources/`, qui s'ouvre dans PRISME comme
dans Obsidian, se modifie et se sauvegarde comme le reste. Sa clé normalisée vit dans
l'en-tête.

```yaml
prisme_type: source
prisme_reference: arxiv:2401.09876     # clé normalisée, sert au dédoublonnage
prisme_genre: arxiv                    # url | doi | arxiv | isbn | texte
prisme_statut: citee                   # citee | ingeree
prisme_relu: false                     # entré tout seul, pas encore validé
prisme_lot: lot-20260918-220334        # identifiant d'annulation
prisme_cite_par: [Veille/Notes.md, Veille/Prospective.md]
prisme_alias: [doi:10.1000/xyz123]     # clés absorbées par une fusion
prisme_fusions: ["doi:…|fichier.md|2026-09-18T22:04|même article"]
```

Le corps porte le titre, la référence et une section **« Citée dans »**. PRISME ne
réécrit que cette section : tout ce que tu ajoutes autour est à toi.

### Deux chemins d'entrée, selon ce qui est vérifiable

| Chemin | Ce qui l'emprunte | Où ça va |
|---|---|---|
| **Balayage** | URL, DOI, identifiant arXiv, ISBN — repérés par expression régulière | Directement dans le vault, `prisme_relu: false`, sous un identifiant de lot |
| **IA** | Ce que le modèle croit reconnaître sans forme vérifiable (« le rapport X ») | File de validation, hors du vault |

La confiance ne vient jamais de l'auto-évaluation du modèle : elle vient de la forme de
la référence. C'est la règle posée par la décision 0021.

**Garde-fou sur les propositions de l'IA.** Chaque proposition doit citer un extrait
littéral de la note. PRISME vérifie que cet extrait s'y trouve vraiment ; sinon la
proposition est écartée sans t'être montrée. Le compte des écartées est affiché.

### Dédoublonnage

Deux notes qui citent la même page ne créent qu'un objet. La normalisation retire ce
qui ne désigne rien :

| Écrit dans la note | Clé retenue |
|---|---|
| `http://www.exemple.org/Page/?utm_source=news&id=7` | `https://exemple.org/Page?id=7` |
| `https://exemple.org/Page?id=7` | la même |
| `arXiv:2401.09876v3` | `arxiv:2401.09876` |
| `https://arxiv.org/abs/2401.09876` | la même — la page et l'identifiant désignent le même travail |
| `https://doi.org/10.1000/xyz` | `doi:10.1000/xyz` |
| `ISBN 978-2-07-036822-8` | `isbn:9782070368228` |

Les adresses locales (`localhost`, hôte sans point) ne sont pas des sources.

### Citée, puis ingérée

Le statut se déduit du registre ENGRAM : si une source importée correspond à la même
référence, l'objet passe à **ingérée** et pointe la note d'import. Rien n'est deviné —
c'est la même clé normalisée, ou rien. Le bouton **↻ Statuts** repasse sur les objets
« citée » quand tu as importé quelque chose depuis.

### Réversibilité partout

- **Annuler un lot** retire d'un coup les objets d'un balayage **encore non relus** ;
  ceux que tu as validés sont conservés. Les notes partent à la corbeille.
- **Retirer un objet** l'envoie à la corbeille et **mémorise le rejet avec sa raison** :
  le balayage suivant ne le recrée pas, et l'IA relit ces raisons avant de proposer.
  L'onglet « Rejets mémorisés » permet de lever un refus.
- **Fusionner** deux objets garde un journal (`prisme_fusions`) et met la clé absorbée
  en alias : elle continue de mener au bon objet. `defusionner` défait l'opération.

### Interface

Un bouton **🔖 Sources citées** dans l'en-tête ouvre une fenêtre à trois onglets :
*Objets Source*, *File de validation*, *Rejets mémorisés*. Filtres par statut et par
état de relecture, gestion des lots, fusion.

Dans l'éditeur, un marqueur **🔖 n** apparaît sur une note qui cite des objets, en ambre
avec un ⚠ quand certains ne sont pas encore relus (décision 0021).

Aucun popup du navigateur : tout passe par `confirmer()` et `demanderTexte()`. Ce
dernier accepte désormais l'option `libre: true`, pour un champ facultatif — une raison
de rejet, par exemple, où exiger une saisie ferait perdre l'action.

## Routes

| Route | Rôle |
|---|---|
| `GET /api/objets/sources` | Objets, lots, comptes (`?statut=`, `?relu=`, `?lot=`) |
| `POST /api/objets/balayer` | Balayage mécanique, entrée directe |
| `POST /api/objets/ia` | Lecture par le modèle, dépôt en file |
| `POST /api/objets/relu` | Marquer relu ou non relu |
| `POST /api/objets/lier` | Rattacher une note d'import, statut « ingérée » |
| `POST /api/objets/supprimer` | Corbeille + rejet mémorisé |
| `POST /api/objets/statuts` | Rafraîchir les statuts depuis ENGRAM |
| `POST /api/objets/lot/annuler` | Annuler un lot (non relus seulement) |
| `GET /api/objets/note?path=` | Les objets cités par une note |
| `GET /api/objets/file` | File de validation et rejets |
| `POST /api/objets/file/accepter` | Accepter, avec correction du titre et de la référence |
| `POST /api/objets/file/rejeter` | Rejeter avec raison |
| `POST /api/objets/file/fusionner` · `/defusionner` | Fusion réversible |
| `POST /api/objets/rejets/oublier` | Lever un refus mémorisé |

## Fichiers

| Fichier | Rôle |
|---|---|
| `prisme_core/objets/detection.py` | Repérage et normalisation des références |
| `prisme_core/objets/file.py` | File de validation et rejets (`~/.prisme/objets/file.json`) |
| `prisme_core/objets/sources.py` | Objets Source comme notes du vault, lots, lien ENGRAM |
| `prisme_core/objets/balayage.py` | Balayage, propositions de l'IA, accepter / rejeter / fusionner |
| `prisme_core/routes/objets.py` | Les routes ci-dessus |
| `prisme_core/web/js/objets.js`, `css/objets.css` | Fenêtre à trois onglets, marqueur de l'éditeur |
| `tests/test_e5_objets.py` | 38 tests |

## Ce qui reste reporté

Les types Décision, hypothèse, prédiction, entité OSINT et tâche (0017). Le mécanisme
de gel est prévu dans le modèle, pas implémenté. Les horloges du monde
(`prisme_valide_du` / `prisme_valide_au`) restent réservées, comme décidé en 0022 : un
objet Source n'a pour l'instant que sa date de publication.

## Vérifié

- 154 tests (`python -m unittest discover -s tests`), dont 38 pour cette étape.
- Parcours complet dans le navigateur : balayage sur deux notes citant les mêmes
  sources, dédoublonnage, marquage relu, filtres, fusion, file de validation,
  acceptation avec correction de référence, rejets, ouverture de l'objet dans l'éditeur,
  marqueur 🔖 sur la note citante.
