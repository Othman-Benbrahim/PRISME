# 0033 · Types d'objets et contrat des prédictions

- **Statut** : implémentée en E11, en revue ; contrôle visuel et Windows restant à faire
- **Écrite** : 2026-09-19

## Problème

Le registre ne sait traiter que les Sources. Décisions, hypothèses, prédictions,
entités et tâches doivent être lisibles sans PRISME et utilisables par les agents,
puis par Constat et un plugin de calibration, sans leur déléguer la validation.

## Décision

- Le cœur définit cinq types, leurs champs, statuts et gabarits Markdown.
  Le contrat est décrit dans `docs/OBJETS.md` et découvert par `/api/v1/types`.
- Les notes portent `prisme_schema: 1`, un identifiant stable et la provenance.
  Elles sont créées dans `Objets/<type>/` du vault principal et restent retrouvables
  après déplacement dans ce vault. Les Sources gardent leur format E5.
- Une fiche d'agent peut être incomplète en file. Son acceptation exige tous les
  champs obligatoires ; l'auteur peut les corriger et conserve l'origine de la proposition.
- Une prédiction porte un événement, une probabilité **entre 0 et 1**, une date
  butoir et un critère de résolution. La résolution ajoute résultat `oui | non |
  indeterminable`, date et preuve. `indeterminable` n'est pas un échec à scorer.
- L'auteur crée ou modifie explicitement une fiche. Seul le bloc balisé de sa fiche
  est régénéré ; les sections libres et propriétés étrangères sont conservées.
  Le retrait va en corbeille avec date d'invalidation et raison.
- L'entrée directe des imports et son seuil se règlent par type. Pour une Source,
  un identifiant reconnu mécaniquement vaut 100/100 **sur la forme**. Cela ne garantit
  ni son accessibilité ni sa véracité. Si l'option est désactivée, le balayage dépose
  les nouvelles Sources en file, avec toutes leurs citations.
- **Aucun signal d'entrée directe n'est défini pour les cinq nouveaux types.**
  Leurs propositions passent toujours en file, même si l'option est activée et le
  seuil mis à zéro. Les réglages sont préparés pour de futurs extracteurs, pas pour
  transformer l'assurance du modèle en preuve. Les agents passent toujours en file.
- Un doublon de type et titre normalisé bloque la création et n'écrase rien.
  Une proposition en conflit reste en file : l'auteur précise son titre ou corrige
  l'objet existant puis rejette la proposition. La fusion automatique reste propre
  aux Sources ; combiner deux paris ou décisions sans règle métier serait trompeur.

## Écarté

- Auto-évaluation du LLM comme signal de confiance.
- Scoring dans le cœur : il reste dans le plugin (0025).
- Activation de l'horloge du monde avant ce plugin (0026).
- Présenter les instantanés comme un gel inviolable. E11 permet encore de modifier
  une prédiction : **pas d'historique scellé, pas de garantie anti-réécriture**.
  Un plugin de calibration devra traiter ce point avant de prétendre mesurer des
  paris fixés à une date. La corbeille et les instantanés actuels ne suffisent pas.
- Étendre la fusion Source à des objets de nature différente sans politique explicite.
