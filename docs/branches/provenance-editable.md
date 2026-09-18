# Provenance modifiable

## Objectif

E3 posait la provenance **à la création** d'une note produite par une machine. Il
manquait le cas inverse : renseigner ou corriger la provenance d'une note qui existe
déjà — un article recopié, une note importée d'un autre outil, une synthèse écrite à
la main. La seule solution était d'écrire le YAML soi-même.

## Ce qui change

**La fiche ⓘ devient modifiable.** Sur une note sans en-tête, le bouton propose
« Ajouter une provenance » ; sur les autres, « Modifier ». Champs saisissables :

| Champ | Note |
|---|---|
| Type | `note`, `source`, `synthese`, `reponse`, `import`, ou le vôtre |
| Produite par | Outil, import, « saisie manuelle »… |
| Modèle, Preset | À laisser vides si aucune IA n'est intervenue |
| Publiée le, Enregistrée le | Dates `AAAA-MM-JJ`, heure facultative |
| Valide du / au | **Réservés** ([0022](../decisions/0022-horloges-des-objets.md)), avec leur état `date` / `inconnue` / `ouverte` |
| Sources | Notes du vault (recherche intégrée) et URLs |

**Un bouton « Poser un identifiant »** sur une note qui n'en a pas : elle devient
citable sans rien ajouter d'autre. L'en-tête ne contient alors que `prisme_id`.

**Les sources se choisissent.** Un champ de recherche interroge l'index : choisir une
note l'ajoute à la liste, et elle recevra son identifiant à l'enregistrement. Une URL
collée est conservée telle quelle. Chaque source se retire d'un clic.

**Validation côté serveur** : seuls les champs prévus sont acceptés (`prisme_id` et
`prisme_sources` ne se saisissent pas à la main), les dates doivent être des dates, et
un état `date` sans date est refusé. Une date renseignée met son état à `date` ;
un état que vous n'avez pas choisi n'est pas écrit.

**Ce qui ne change pas** : seule l'en-tête est écrite, le corps de la note n'est jamais
touché, un instantané est pris avant chaque écriture, et l'index est prévenu — y
compris pour les notes citées, dont l'identifiant vient d'être posé.

**Correction au passage** : le badge 🤖 ne s'affiche plus que si un **modèle** est
intervenu. Un outil seul (« saisie manuelle », un import) affiche ⓘ. La fiche affiche
aussi les champs que l'index ne stocke pas (dates de validité, publication), car
l'en-tête du fichier fait désormais foi.

## Fichiers touchés

**Créés** : `tests/test_provenance_editable.py`, ce fichier.
**Modifiés** : `prisme_core/provenance.py` (validation et écriture),
`prisme_core/routes/files.py` (`POST /api/provenance`, GET enrichi),
`prisme_core/web/js/provenance.js`, `prisme_core/web/css/editeur.css`,
`docs/ARCHITECTURE.md`, `docs/RUPTURES.md`, `docs/FEUILLE-DE-ROUTE.md`,
`PLUGIN-DEVELOPMENT.md`.

## Tester

```powershell
python -m unittest discover -s tests -v
python prisme.py
```

93 tests, dont 9 pour cette branche (validation, ajout, correction, retrait de
champs et de sources, mise à jour de l'index, erreurs, identifiant seul).

Vérifications manuelles :

1. Ouvrir une note écrite à la main, ⓘ, « Ajouter une provenance » : renseigner le
   type et une source, enregistrer. L'en-tête doit apparaître dans l'éditeur, et le
   corps être inchangé.
2. Rouvrir la fiche : les champs doivent être relus, la source cliquable.
3. « Modifier », vider un champ, enregistrer : la clé doit disparaître de l'en-tête.
4. Saisir une date invalide : l'erreur doit s'afficher sans rien écrire.
5. Sur une autre note, « Poser un identifiant » : l'en-tête ne doit contenir que
   `prisme_id`.
6. Vérifier dans Obsidian que le panneau Propriétés affiche bien ces champs.

Vérifié ici dans un navigateur réel : ajout complet avec URL et note du vault,
recherche de source, retrait d'une source, erreur de date, identifiant seul, aucune
erreur JavaScript.

## Limites

- Les modifications de l'en-tête ne sont pas historisées autrement que par les
  instantanés de `.trash/versions/`.
- Si une note ouverte a des modifications non enregistrées au moment où vous écrivez
  sa provenance, elles sont remplacées par la version du disque — un avertissement
  s'affiche alors.
- `prisme_sources` accepte les identifiants de notes et les URLs ; il n'y a pas encore
  de vérification que l'URL existe.
