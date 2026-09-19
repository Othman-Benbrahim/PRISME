# Constat — passages, contradictions et transfert vers Calibration

Branche : `constat-suite` · Base : E9 fusionnée (PR #22).

Les changements et leurs limites sont décrits dans la
[décision 0038](../decisions/0038-constat-preuves-et-calibration.md).
Les guides [Constat](../../guides-plugins/constat.md),
[Calibration](../../guides-plugins/calibration.md) et
[OSINT Cross-Reference](../../guides-plugins/osint-cx.md) sont actualisés.

## Vérification visuelle Windows

Utiliser un atelier et un vault d'essai distincts de vos données habituelles.
Le binaire E9 déjà extrait ne contient pas cette évolution : utiliser l'archive
construite pour cette branche, avec son dossier `plugins/` et `_internal/`.

1. Ouvrir **Constat → Créer un dossier de démonstration**. Vérifier les trois
   sources fictives et les trois citations dans **Passages sources et contradictions**.
2. Ouvrir **Relier une preuve à un passage exact**, choisir une preuve et copier
   une phrase de la source affichée. Motiver l'ajout. La nouvelle révision doit
   être non validée ; l'ancienne reste dans **Historique complet**.
3. Essayer un extrait inventé dans une correction JSON : la sortie doit être
   incomplète et ne pas offrir de versement. Corriger avec un extrait exact,
   puis valider. Ne pas inventer de citation dans un dossier réel.
4. Dans ce dossier fictif seulement, essayer le formulaire de contradiction.
   Le signalement et son motif doivent apparaître ; sa correction conserve la trace.
5. Valider l'ACH, verser une hypothèse, saisir `0,8`, une échéance future, un
   critère observable et le domaine `Test`. Aucun résultat observé n'est prérempli.
6. **Actualiser les prédictions de ce dossier** : la proposition attend une
   acceptation explicite. L'accepter, relire les pièces, conserver les bornes du
   monde inconnues si elles le sont, puis confirmer séparément la copie.
7. Ouvrir Calibration : le pari doit être présent avec ses pièces, mais sans score
   tant qu'il n'est pas résolu. Pour un essai fictif « oui », suivre le guide :
   Brier `0,0400`, log loss `0,2231`. Ne jamais simuler la résolution d'un vrai pari.
8. Fermer et rouvrir PRISME : retrouver le dossier, les citations, le motif,
   les validations et la copie. Le JSON exporté doit conserver l'historique.
9. Désactiver Calibration puis recharger Constat : le dossier reste utilisable et
   le panneau explique l'absence du plugin. Réactiver ensuite Calibration.
10. Dans OSINT, vérifier les options restantes, notamment GitHub, Wikidata,
    Entreprises, X, LinkedIn et les outils locaux. L'ancien connecteur n'apparaît
    plus, y compris dans **Plugins → Secrets**. Ne lancer que les recherches utiles.

Le test de démonstration ne nécessite aucun modèle IA ni appel à un fournisseur.
Les tests automatiques refusent également un journal réécrit, une proposition
modifiée depuis sa relecture et un transfert depuis un autre vault.

## Vérifications de développement

```powershell
python -m unittest discover -s tests
npm ci --prefix plugins/constat
npm test --prefix plugins/constat
git diff --check
```

La publication d'une release et la fusion de cette branche restent des étapes
séparées de la vérification. Une copie de calibration n'est pas un horodatage
certifié ; ses empreintes protègent contre les altérations accidentelles.

## Contrôles effectués avant la PR

- 436 tests Python : réussis, deux tests propres à Windows ignorés sous Linux.
- 141 tests JavaScript : réussis, dont dépôt, acceptation, copie et plugin absent.
- Parcours dans Chromium sur un profil et un vault temporaires : démonstration,
  citations, correction avec contradiction, validation, proposition, acceptation,
  copie des pièces, résolution fictive et affichage des scores (`0,0400` / `0,2231`).
- Rendu des passages vérifié à 1280 px et 390 px ; persistance après rechargement.
- Les contrôles Windows et le build du binaire sont exécutés par GitHub Actions.

L'essai du navigateur porte sur Constat, Calibration et l'ouverture d'OSINT. Le
chargement du graphe général dépend de son CDN D3, inaccessible dans cet environnement
de contrôle ; ce graphe ne fait pas partie des changements de cette branche.
