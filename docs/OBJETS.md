# Objets typés — contrat E11, version 1

Ouvrir **Sources citées → Types d’objets → Créer un objet**. Dans la fenêtre,
« Objets du vault » regroupe les Sources, la file commune et les types E11.
Chaque fiche devient une note Markdown du vault principal. Le panneau permet de
modifier ses champs ; les sections libres restent éditables dans l'éditeur ordinaire.
Les champs structurés sont des scalaires sur une ligne (4 000 caractères maximum,
200 pour le titre). Les développements longs vont dans les sections libres.

## Types et champs

Les noms ci-dessous s'emploient dans `champs` pour l'API. Dans le frontmatter, ils
portent le préfixe `prisme_`. `titre` est à la racine du corps JSON.

| Type | Champs obligatoires | Champs facultatifs | Statuts |
|---|---|---|---|
| `decision` | `choix`, `justification` | `alternatives`, `decide_le` | `active`, `remplacee`, `annulee` |
| `hypothese` | `enonce`, `critere_refutation` | `indices` | `a_examiner`, `corroboree`, `refutee`, `abandonnee` |
| `prediction` | `enonce`, `probabilite`, `echeance`, `critere_resolution` | `domaine`, `hypothese`, `resultat`, `resolu_le`, `preuve_resolution` | `ouverte`, `resolue`, `annulee` |
| `entite` | `nature`, `description` | `identifiant_externe`, `alias` | `active`, `archivee` |
| `tache` | `action`, `critere_fin` | `responsable`, `echeance` | `a_faire`, `en_cours`, `terminee`, `annulee` |

Le premier statut est la valeur par défaut. Les dates sont réelles, au format
`AAAA-MM-JJ`. Une échéance passée reste autorisée pour reprendre un ancien pari ;
la date d'enregistrement est celle de son entrée effective dans PRISME.

`nature` vaut `personne`, `organisation`, `lieu`, `produit` ou `autre`.
`probabilite` est un nombre fini entre 0 et 1, bornes incluses, jamais un pourcentage.
Une prédiction résolue exige les trois champs `resultat` (`oui`, `non` ou
`indeterminable`), `resolu_le` et `preuve_resolution`. Les autres statuts n'admettent
aucun de ces champs. La résolution est un jugement explicite de l'auteur ; le cœur
ne vérifie pas la vérité de sa preuve et ne calcule aucun score.

## Propositions des agents, dont Constat

`GET /api/v1/types` expose les champs et statuts. Le droit `lecture` suffit.
`POST /api/v1/proposer`, avec le droit `proposition`, reçoit par exemple :

```json
{
  "type": "prediction",
  "titre": "Rétablissement du service le 2 janvier",
  "champs": {
    "enonce": "Le service répondra à midi UTC",
    "probabilite": 0.7,
    "echeance": "2027-01-02",
    "critere_resolution": "HTTP 200 sur la page de statut à 12 h UTC",
    "domaine": "disponibilité"
  },
  "motif": "Hypothèse issue du dossier Constat"
}
```

Une proposition peut omettre les champs que l'auteur doit compléter. Les champs
fournis sont déjà contrôlés : `NaN`, une fausse date, un statut ou champ inconnu sont
refusés. Le client ne peut fixer ni l'origine, ni l'identifiant, ni la validation.
`note` désigne facultativement une note du vault principal ; si `indice` est fourni
avec elle, l'extrait doit s'y trouver littéralement. L'absence d'une note locale est
permise pour un client extérieur tel que Constat.

La réponse 201 signifie **en file**, jamais « écrit dans le vault ». La réponse 409
signifie déjà en file, rejet mémorisé ou plafond par origine atteint. La file propre
à la clé reste accessible par `GET /api/v1/file`.

Dans **File de validation**, l'auteur clique **Relire et compléter**, corrige et
valide. En cas d'erreur, la proposition reste en file. Un refus mémorise sa raison.
L'API de session pour cette acceptation est `/api/objets/file/accepter` ; la clé d'un
agent ne permet pas de l'appeler.

`GET /api/v1/objets` conserve la clé `sources` d'E6 et ajoute `objets`. Le filtre
`?type=prediction` renvoie les prédictions. Les objets E11 ont un chemin relatif avec
barres obliques, un `id` stable, un `type`, un `titre`, une `cle` et leurs `champs`.
Le registre parcourt le vault principal selon le plafond existant de 5 000 notes.

MCP : `prisme_types` découvre le contrat, `prisme_objets` lit les objets,
`prisme_proposer` accepte désormais `type` et `champs`. Sans `type`, il garde le
comportement Source d'E10. L'adaptateur reste sans dépendance tierce.

## Notes, modifications et limites

La note porte `prisme_schema: 1`, `prisme_id`, `prisme_type`, `prisme_titre`,
`prisme_cle`, `prisme_relu`, `prisme_origine`, `prisme_enregistre_le` et les champs
du type. Une acceptation d'agent conserve son origine dans `prisme_genere_par`, la
clé de proposition et le contexte fourni. La raison de validation est conservée.

`prisme_id` ne change pas quand on renomme la fiche ; `prisme_cle`, dérivée du type
et du titre normalisé, change. Elle sert au dédoublonnage et aux actions de session,
**pas** comme identifiant externe durable. Un titre similaire provoque une relecture,
jamais une fusion automatique. Deux paris distincts demandent des titres distincts.

Les propriétés sont la source structurée. Le bloc entre `<!-- prisme:fiche -->`
et `<!-- /prisme:fiche -->` en est une présentation régénérée par le formulaire.
Si vous retirez les balises, PRISME conserve le corps au lieu de l'écraser.
Ne supprimez pas ces balises si vous souhaitez continuer à synchroniser ce bloc.
Les sections libres sont conservées ; les champs étrangers au contrat aussi.

Les écritures directes manuelles ou d'un agent disposant du droit `ecriture`
restent des éditions Markdown générales. Leur contenu n'est pas certifié par le
contrat E11 : un futur plugin doit valider les propriétés avant de scorer.
Les modifications utilisent les instantanés existants ; ils ne sont pas un journal
inviolable et peuvent se recouvrir lors d'écritures dans la même seconde.

Le gel, l'archivage probant des paris, la calibration, l'horloge du monde et la
fusion réversible des nouveaux types restent hors périmètre. Aucune mesure de
calibration n'est promise par cette étape.
