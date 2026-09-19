# 0038 — Constat : passages exacts et pièces du pari

Date : 2026-09-19 · Statut : implémentée sur `constat-suite`, en vérification.

## Pourquoi

Une référence de source dans une ACH ne permet pas toujours de retrouver le
passage qui soutient une affirmation. Les corrections doivent rester explicables,
et le transfert d'une hypothèse vers Calibration doit conserver les pièces de
l'analyse. L'auteur a demandé cette suite après E9, ainsi que le retrait du
connecteur obsolète d'OSINT Cross-Reference.

L'inspiration retenue d'[Utopia](https://github.com/deeplethe/utopia) est la
traçabilité des assertions, des conflits et de leur validation humaine. Aucun
code, serveur, moteur de graphe, PostgreSQL ou Docker de ce projet n'est importé.

## Décision

- Les preuves ACH et les affirmations factuelles peuvent référencer des passages
  exacts : source, SHA-256 du corps brut, extrait et positions UTF-16. Un passage
  inexistant, ambigu sans position ou d'une autre version bloque la validation.
  Les anciennes analyses sans passages sont conservées et explicitement signalées.
- Une citation atteste le contenu d'un document, sans convertir son affirmation
  en vérité établie. Les inférences restent dans les analyses attribuées.
- Les contradictions entre preuves sont proposées par le modèle ou déclarées
  par l'auteur, avec un motif. Elles ne sont pas résolues automatiquement et restent
  distinctes des cases d'incompatibilité de la matrice ACH.
- Les corrections exigent un motif et produisent une révision non validée.
  Les analyses, corrections et validations antérieures restent consultables.
  Le serveur impose les ajouts au journal ; la base locale n'est pas inviolable.
- Proposer un pari produit une note de pièces dans le vault. La file conserve ce
  lien lors de l'acceptation. Depuis Constat, deux gestes explicites permettent
  d'accepter la fiche Prédiction, puis de figer le pari et ses pièces dans Calibration.
- Calibration archive les pièces avec leur empreinte avant résolution. Une note
  ou des pièces modifiées depuis la relecture imposent une actualisation. Après
  copie, leur suppression à l'origine ne supprime pas les preuves archivées.
- Le cœur ne contient aucun calcul de calibration. Constat ne déduit ni probabilité
  depuis le score ACH, ni résultat observé. L'horloge du monde reste explicitement
  renseignée lors de la copie ; ses bornes peuvent rester inconnues.
- Une interface Constat ouverte sur un ancien vault est refusée avant tout appel
  d'acceptation ou d'inscription dans un autre vault.
- L'intégration OSINT retirée n'a plus de routes, secret déclaré, réglage, champ
  d'interface, appel réseau ni documentation. Les autres connecteurs sont conservés.

## Compatibilité et limites

Pas de nouvelle base ni de migration des objets E11. Les anciennes copies de
Calibration restent lisibles ; le champ optionnel `pieces_constat` complète le
format version 1. Les anciens paris sans pièces ne sont pas enrichis rétroactivement.
Constat reste opérationnel sans le plugin Calibration, et les archives de celui-ci
se lisent sans Constat.

Les corps nouvellement importés sont hachés sans normalisation : deux textes qui
ne diffèrent que par les espaces ou les retours à la ligne gardent des versions
séparées. Les outils de comparaison textuelle conservent leur normalisation propre.
Les exports du dossier gardent les corps et l'historique complets. Le rapport de
pièces est limité à 200 ko (210 ko avec provenance), sans troncature silencieuse.

Les écritures de proposition et d'archive traversent plusieurs composants : il
n'y a pas de transaction distribuée. Après une coupure, actualiser le panneau
retrouve les propositions et fiches existantes. Un rapport créé juste avant un
échec peut rester dans `Rapports/` ; il n'est pas supprimé automatiquement.

La fusion d'entités, le graphe bitemporel complet et les déductions automatiques
à la manière d'Utopia ne font pas partie de cette évolution.
