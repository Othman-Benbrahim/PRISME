# Calibration des prédictions

Plugin facultatif (0025) après E11. Aucun appel de modèle ni dépendance supplémentaire.
Il calcule les scores ; E11 conserve seulement le contrat des objets.

## Parcours

1. Créer ou accepter une prédiction E11, avec probabilité entre 0 et 1, date butoir
   et condition vérifiable de résolution. La prédiction doit être relue et ouverte.
2. Ouvrir **Calibration**, puis **Préparer la copie**. Confirmer les bornes du monde :
   `date`, `inconnue` ou `ouverte`. Une borne inconnue ne signifie pas « toujours vrai ».
   La date butoir du pari et la validité de l'énoncé dans le monde sont distinctes.
3. Confirmer **avant le jour de l'échéance (UTC)** et avant de connaître le résultat.
   La copie va dans `Objets/Calibration/<id>.md`. Une seconde inscription n'écrase rien.
4. Après observation, résoudre la prédiction dans Types d'objets : oui, non ou
   indéterminable, date et preuve. Actualiser Calibration.
5. Consulter les agrégats ou **Enregistrer le rapport Markdown** dans `Rapports/`.

L'inscription est explicite : ni acceptation d'une proposition ni installation du
plugin ne créent automatiquement une copie. Une prédiction déjà résolue ne peut
pas recevoir rétrospectivement sa copie. Une ancienne prédiction ouverte peut être
inscrite aujourd'hui ; son horizon sera mesuré depuis cette inscription.

## Mesures

Pour un résultat binaire y (oui=1, non=0) : Brier `(p-y)²`, log loss
`-ln(p)` si oui, `-ln(1-p)` si non. Une certitude fausse donne une log loss infinie,
représentée par la chaîne JSON `infini` et par ∞ à l'écran ; aucune troncature cachée.
Plus bas est meilleur pour ces deux pertes. Un groupe vide reste « Non calculé ».

Rapports globaux et par domaine/horizon, avec effectifs, probabilité moyenne,
fréquence, biais moyen `p-y` et dix classes de probabilité. L'ECE est la moyenne
pondérée des écarts absolus entre probabilité et fréquence dans ces classes.
Les classes sont `[0;0,1[`, …, `[0,9;1]`. Horizon en jours calendaires UTC entre
copie et échéance : 0–7, 8–30, 31–90, 91 et plus (l'inscription impose au moins 1 jour).
Le biais positif signale une surestimation moyenne dans cet échantillon ; il ne
prouve pas un biais systématique. Aucun test de significativité n'est annoncé.

Banc rejouable : p=0,8 → oui ; p=0,6 → non. n=2 ; Brier=0,2 ;
log loss=0,5697171416 ; biais=0,2 ; ECE=0,4.

## Horloges et exclusions

Les quatre champs E3 sont activés par l'inscription, sans migration. Les dates
restent des dates ISO ; une borne ouverte ou inconnue n'a pas de valeur de date.
Le filtre « Validité dans le monde » utilise les bornes de la copie, avec extrémités
incluses. Vide : aucun filtre. Une validité inconnue est exclue d'un filtre daté.
Cela ne reconstruit pas ce que PRISME savait autrefois.

Sont exclus et expliqués : absence de copie, fiche non relue ou invalide, copie
illisible/altérée/dupliquée, identifiant d'objet absent ou dupliqué, pari modifié,
statut ouvert ou annulé, résultat indéterminable, résolution antérieure à la copie
ou future, validité hors période/inconnue si un filtre est demandé.
Le déplacement d'une fiche ne casse pas sa relation : l'identifiant est stable.
Énoncé, probabilité, échéance, condition, domaine et référence d'hypothèse sont
comparés à la copie. Changer un pari demande une nouvelle prédiction.

La copie locale datée et son empreinte détectent une altération accidentelle,
**pas une falsification volontaire** : l'auteur peut réécrire les deux. Ce n'est
ni un service d'horodatage ni un gel probant. Le plugin ne sait pas si l'auteur
connaissait déjà le résultat. Les dates de résolution E11 n'ont pas d'heure ;
il ne peut donc pas distinguer deux événements d'une même journée.

La désactivation du plugin retire ses routes et son interface ; prédictions,
copies et rapports restent lisibles en Markdown. Aucun score n'est écrit dans
les champs E11. Copies et rapports sont estampillés comme calcul local sans modèle.

## API publique des plugins ajoutée

- `ctx.typed_object(path)` : lecture et validation du contrat E11.
- `ctx.set_world_clock(path, fields)` : écriture des quatre bornes/états, permission
  `vault_write`, types décision/prédiction seulement. L'interface de ce plugin
  l'utilise pour les prédictions ; les décisions ne sont pas scorées.
- `ctx.write_note(..., exclusive=True)` : refuse toute note déjà présente.
- `update_frontmatter` exporté par `prisme_core.api`.

Routes de session sous `/api/plugins/calibration/` : GET `predictions`, POST
`inscrire` (chemin, version SHA-256 du texte lu, horloge), GET `rapport?jour=`,
POST `exporter` (jour facultatif). Une clé d'agent ne permet pas cette inscription.
