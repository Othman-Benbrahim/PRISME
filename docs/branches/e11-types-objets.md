# E11 — Types d'objets

## Objectif

Le vault sait maintenant représenter les décisions, hypothèses, prédictions, entités
et tâches avec un contrat commun au formulaire, à l'API et aux futurs plugins.
Les agents peuvent proposer ces objets ; l'auteur complète et valide les champs.
La décision [0033](../decisions/0033-types-objets.md) fixe les limites et le
[contrat](../OBJETS.md) documente les propriétés.

## Fichiers touchés

- Créés : `objets/types.py` (contrat), `registre.py` (notes), `reglages.py` (seuils),
  `routes/types_objets.py`, `web/js/types-objets.js`, `web/css/types-objets.css`,
  `tests/test_e11_types.py`, `docs/OBJETS.md` et décision 0033.
- Modifiés : assemblage Flask, provenance, file, balayage Sources, routes objets et
  agents, interface objets, adaptateur MCP et son banc, documentation de suivi.
- Deux corrections ciblées : les Sources lues honorent `safe_path` même à travers un
  lien symbolique ; les scalaires à guillemets relisent correctement les antislashs.
- Aucun fichier supprimé. Aucune dépendance ajoutée. `vault.py` et `core.css` inchangés.

## Ruptures

Aucune migration : Sources E5 et propositions E6/E10 sans `type` restent reconnues.
`GET /api/v1/objets` ajoute la clé `objets` sans retirer `sources`.
Le réglage par défaut conserve l'entrée directe des Sources ; le désactiver envoie
les nouvelles références mécaniques en file. Les cinq nouveaux types attendent
obligatoirement une validation, quel que soit le seuil choisi.

## Tester

```powershell
python -m unittest discover -s tests -p "test_e11_types.py" -v
python -m unittest discover -s tests
```

Résultat du banc Linux Python 3.12 : **386 tests, 367 réussis, 19 ignorés**.
E11 ajoute 25 tests métier et 2 parcours MCP : cinq formats, probabilités bornées et finies, dates réelles,
refus des injections YAML, résolution complète, conservation des notes libres et
identifiants, déplacements, doublons, file incomplète, provenance d'agent,
non-contournement par le droit d'écriture ou un seuil nul, lecture API, racines et
liens symboliques, réglages et régression Sources. Les tests de liens peuvent être
ignorés sous Windows sans privilège de création de liens.

**Limites de vérification :** pas d'exécution Windows ni PowerShell disponible ici.
Le navigateur local n'était pas installé et son téléchargement a échoué ; le
navigateur distant a refusé localhost (`ERR_BLOCKED_BY_CLIENT`). Le contrôle visuel
obligatoire n'a donc pas été réalisé. Cette étape reste **en revue**, pas « faite ».

Parcours manuel avant fusion, dans un vault d'essai :

1. Ouvrir Sources citées, puis Types d'objets. Créer un objet de chaque type ; les
   champs obligatoires empêchent une fiche vide. Ouvrir la note produite.
2. Ajouter un paragraphe libre, rouvrir la fiche, changer le statut : le paragraphe
   et l'identifiant doivent rester. Essayer un titre avec accents, apostrophe et guillemets.
3. Créer une prédiction à 0 puis à 1 ; essayer 1,2 (refus). Tester une résolution
   sans preuve (refus), puis avec résultat, date et preuve (acceptation).
4. Proposer une prédiction incomplète par `/api/v1/proposer` : aucun fichier créé.
   Dans la file, la compléter, valider ; vérifier origine et raison dans la note.
5. Dans Entrée directe, désactiver Sources ; balayer deux notes citant la même URL :
   une proposition, puis deux citations conservées après acceptation.
6. Rejeter une proposition avec raison ; vérifier l'onglet Rejets et l'absence de
   reproposition. Retirer une fiche créée : vérifier sa présence dans la corbeille.
7. Vérifier le défilement de la fiche Prédiction, les boutons, cases à cocher,
   superposition des dialogues et absence d'erreur dans la console du navigateur.

## Hors périmètre

E9 attend les précisions de l'auteur. Pas de release ni de build. Le plugin de
calibration et le bouton Constat ne sont pas livrés ici. L'horloge du monde reste
inactive (0026). Le gel et la fusion réversible des types E11 restent reportés : les
instantanés actuels ne sont pas un archivage probant des prédictions.
