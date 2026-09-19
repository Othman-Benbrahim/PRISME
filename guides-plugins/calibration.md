# Calibration — obtenir et interpréter des scores de prédiction

[Retour aux guides](README.md)

## Comprendre les quatre moments

Le plugin compare une probabilité annoncée à un résultat observé. Il calcule
localement les scores, sans modèle IA, sans clé API et sans service distant.

1. **Créer ou accepter** une prédiction E11 complète et relue.
2. **Copier le pari** dans Calibration alors qu'il est ouvert, avant le jour de
   l'échéance et avant de connaître le résultat.
3. **Résoudre la prédiction** après observation, avec un résultat et une preuve.
4. **Actualiser le rapport** pour calculer les scores admissibles.

Accepter une proposition venant de [Constat](constat.md) ne crée pas sa copie de
calibration. Une prédiction résolue avant inscription ne peut pas être copiée
rétrospectivement pour obtenir un score.

## Premier score : exemple fictif

Faites ce test dans un vault d'essai, pour ne pas mélanger des résultats simulés
avec vos vraies prévisions. Le pari doit permettre une résolution anticipée
lorsque l'événement se produit avant sa date butoir.

1. Dans **Types d'objets**, créez une **Prédiction**, ou acceptez celle proposée
   par le dossier de démonstration Constat.
2. Utilisez un énoncé fictif, par exemple « Un message de confirmation sera reçu
   avant la date butoir ». Saisissez **0,8** comme probabilité, une date butoir
   demain ou plus tard, et un critère explicite : « Oui si le message de confirmation
   est reçu avant cette date ; non sinon ». Gardez le statut **ouverte** et les
   champs de résolution vides. Indiquez le domaine **Test** pour reconnaître l'essai.
3. Ouvrez **Calibration → Préparer la copie** sur cette prédiction.
4. Pour cet exemple, choisissez **Sans borne de début** et **Sans borne de fin**,
   puis **Confirmer les bornes et copier le pari**.
5. Vérifiez **Copie de référence présente**. La copie est enregistrée dans
   `Objets/Calibration/` ; ne la modifiez pas.
6. Pour simuler la réception du message dans cet essai, retournez dans
   **Types d'objets → Modifier la fiche**. Choisissez le statut **resolue**, le
   résultat **oui**, la date du jour et la preuve « Simulation fictive du message
   reçu, uniquement pour vérification ». Enregistrez.
7. Ouvrez **Calibration → Actualiser**, avec le filtre de validité laissé vide.

Résultat attendu :

| Mesure | Valeur affichée |
|---|---|
| Prédictions scorées | 1 |
| Brier | 0,0400 |
| Log loss | 0,2231 |
| Biais moyen | −0,2000 |

Pour vérifier une moyenne, créez un **second pari distinct** à 0,6, copiez-le,
puis résolvez-le « non » avec un motif explicitement fictif. Avec ces deux seuls
paris scorés : **Brier = 0,2000**, **log loss ≈ 0,5697**, biais moyen = 0,2000.
Cette simulation teste le calcul ; dans vos dossiers réels, attendez une observation
permettant effectivement de trancher le critère.

## Échéance et horloge du monde

L'inscription doit avoir lieu **avant le jour de l'échéance, en UTC**. Une date
butoir fixée à aujourd'hui est donc refusée, même si l'heure que vous aviez en tête
n'est pas encore passée. L'horizon utilisé dans les statistiques commence à la
copie, pas à une date de rédaction supposée.

Les bornes de l'horloge du monde décrivent la validité de l'énoncé. Elles sont
indépendantes de l'échéance du pari :

| État d'une borne | Signification |
|---|---|
| Date connue | Vous renseignez une date de début ou de fin |
| Inconnue | Vous ne savez pas situer cette borne |
| Sans borne de début / de fin | Vous indiquez explicitement une borne ouverte |

Ne remplacez pas une date inconnue par une borne ouverte pour faire entrer un
pari dans un filtre. Laissez **Inconnue** lorsque vous ne savez pas.

Le filtre **Validité dans le monde à la date** sélectionne les copies dont les
bornes couvrent cette date, extrémités comprises. Une validité inconnue peut
entraîner une exclusion. **Date vide : aucun filtre de validité.** Ce filtre ne
reconstitue pas ce que vous saviez à une date passée.

## Résoudre un vrai pari

Dans **Modifier la fiche**, conservez l'énoncé, la probabilité, l'échéance, le
critère et le domaine copiés. Renseignez le statut, le résultat, la date et une
preuve vérifiable : document, lien, constat daté ou explication de l'observation.

- **oui** ou **non** : permettent un score binaire si les autres conditions sont remplies ;
- **indeterminable** : conserve une résolution qui ne permet pas de trancher, sans score ;
- **annulee** : exclut le pari ; n'en faites pas un résultat négatif artificiel.

Un changement de probabilité après la copie exclut le pari des scores. Si votre
prévision évolue, formulez une nouvelle prédiction au lieu de réécrire le pari
historique. Une seconde inscription ne remplace pas la copie existante.

## Lire les chiffres

Pour `oui`, le résultat vaut 1 ; pour `non`, il vaut 0.

| Mesure | Calcul ou lecture |
|---|---|
| Brier | `(probabilité − résultat)²` ; plus faible est meilleur |
| Log loss | `−ln(p)` pour oui, `−ln(1−p)` pour non ; plus faible est meilleur |
| Biais moyen | Moyenne de `p − résultat` ; positif signifie une surestimation moyenne dans cet échantillon |
| Classes de calibration | Compare la probabilité moyenne annoncée à la fréquence observée dans chaque tranche |
| ECE du rapport exporté | Moyenne pondérée des écarts absolus dans les dix classes de probabilité |

Une certitude fausse (`p = 1` puis non, ou `p = 0` puis oui) donne une **log loss ∞**.
Ce n'est pas un bug et la valeur n'est pas remplacée par un nombre arbitraire.
Sans pari admissible, **Non calculé** est normal ; ce n'est pas un score égal à zéro.

Les tableaux regroupent aussi les résultats par **domaine** et par **horizon à la
copie** : 0–7, 8–30, 31–90 et 91 jours ou plus. Le graphique compare probabilités
annoncées et fréquences observées. Un point près de la diagonale sur un très petit
échantillon ne démontre pas une bonne calibration durable : regardez les effectifs.

## Exclusions : comprendre pourquoi un score manque

| Raison possible | Action utile |
|---|---|
| Prédiction encore ouverte | Attendre l'observation, puis renseigner sa résolution |
| Pas de copie avant résolution | Conserver cette fiche ; inscrire vos prochains paris avant de les résoudre |
| Pari modifié après copie | Examiner les modifications ; créer un nouveau pari pour une nouvelle prévision |
| Résultat indéterminable ou pari annulé | Exclusion normale des scores binaires |
| Date de résolution future ou antérieure à la copie | Corriger une erreur de date avec la date réelle, sans antidater |
| Filtre incompatible ou validité inconnue | Examiner les bornes ; retirer le filtre pour voir l'ensemble admissible |
| Copie altérée, dupliquée ou objet non identifiable | Examiner les fichiers et leurs identifiants ; ne pas reconstruire une copie après coup pour forcer le score |
| Aucune prédiction valide et relue | Compléter ou accepter la fiche via Types d'objets et la file de validation |

Le tableau **Exclusions** donne la raison pour chaque note écartée. Les paris exclus
ne sont pas comptés comme des zéros dans les moyennes.

## Sauvegarder et limites

**Enregistrer le rapport Markdown** crée un document dans `Rapports/`, avec les
scores, groupes, classes, preuves et exclusions. Sauvegardez ensemble les fiches
Prédiction, leurs copies dans `Objets/Calibration/` et les rapports utiles.
La désactivation du plugin laisse ces fichiers lisibles en Markdown.

Les copies sont locales et munies d'une empreinte. Elles détectent des altérations
accidentelles, mais ne sont pas un horodatage certifié ni une archive inviolable.
Le plugin ne peut pas savoir si vous connaissiez déjà le résultat lors de la copie.
Les dates de résolution n'ont pas d'heure : l'ordre de deux événements d'une même
journée n'est pas démontré par ces seules dates.

**Repère de réussite :** un pari copié avant résolution obtient le score attendu,
les exclusions sont expliquées et les mêmes résultats sont conservés dans le rapport.
