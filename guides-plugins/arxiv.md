# ArXiv — chercher des publications depuis une note

[Retour aux guides](README.md)

## À quoi sert ce plugin ?

**ArXiv** transforme le sujet de la note ouverte en requête scientifique, affiche
les publications trouvées, puis permet d'en demander une synthèse en français.
L'analyse utilise les **résumés fournis par arXiv**, pas une lecture intégrale des PDF.

## Préparer

- Ouvrez une note `.md` contenant un sujet suffisamment précis.
- Configurez et testez le modèle IA dans PRISME.
- Une connexion Internet est nécessaire pour interroger arXiv. Aucune clé arXiv
  n'est demandée par ce plugin ; le fournisseur IA peut demander sa propre clé.

Le parcours normal commence par un appel IA : sans modèle disponible, le bouton
ne constitue pas un moteur de recherche scientifique autonome.

## Première recherche

1. Dans une note d'essai, écrivez quelques phrases sur un sujet, par exemple
   « Détection d'anomalies dans des séries temporelles, avec peu de données annotées ».
2. Cliquez sur **ArXiv**. Gardez cette note ouverte pendant le parcours.
3. Dans **Indication**, précisez l'angle souhaité : « Comparer méthodes statistiques
   et apprentissage profond ; rechercher les limites expérimentales ».
4. Choisissez le nombre de papiers, par exemple **5**, puis **Lancer la recherche**.
5. Lisez la **Requête générée**. Examinez titres, dates, auteurs et résumés ;
   **Tout afficher** déplie un résumé et le lien **ArXiv** ouvre la source.
6. Cliquez sur **Synthétiser** pour lancer le second appel IA.
7. Relisez les citations `[1]`, `[2]` et les affirmations avant de cliquer sur
   **Sauver comme .md**.

La recherche et la synthèse sont deux actions distinctes. Voir les cartes des
papiers ne signifie pas qu'une synthèse a déjà été produite.

## Lire et conserver le résultat

La note enregistrée se trouve dans le dossier actuellement affiché dans
l'explorateur, sous un nom commençant par `arxiv-`. Elle comprend le lien vers la
note de départ, la requête, la synthèse et la liste brute des références. La
provenance de génération est enregistrée. La note de départ n'est pas remplacée.

Une référence exacte peut accompagner une interprétation erronée du modèle.
Ouvrez le papier pour vérifier méthode, population étudiée, résultats et limites.
Le plugin ne certifie ni la qualité scientifique ni l'évaluation par les pairs.

## Données envoyées et limites

Le modèle reçoit un extrait de la note pour construire la requête, puis du contexte
et les résumés pour la synthèse. La génération de requête utilise au plus les
**4 000 premiers caractères** de la note : placez le sujet principal au début.
La requête est ensuite envoyée à arXiv. Avec une IA distante, son extrait de contexte
lui est transmis également.

Le nombre demandé est un maximum souhaité, pas une promesse de résultats pertinents.
Une indication de période donnée à l'IA ne garantit pas un filtrage parfait :
contrôlez les dates affichées.

## Dépannage

| Symptôme | Que faire ? |
|---|---|
| « Ouvrez d'abord un fichier .md » | Ouvrir une note avant de cliquer sur ArXiv |
| Échec de génération de requête | Utiliser **Test API IA**, puis vérifier **Paramètres** |
| Requête générée, mais arXiv échoue | Simplifier le champ proposé et cliquer **Relancer ArXiv avec cette requête** |
| Aucun papier | Élargir le sujet, réduire les contraintes et contrôler la requête anglaise |
| Attente ou limitation du service | Utiliser **Test ArXiv**, puis attendre avant de recommencer |
| Pas de bouton de sauvegarde | Produire d'abord une synthèse avec **Synthétiser** |

**Repère de réussite :** des références accessibles, une synthèse produite après
votre clic et une nouvelle note contenant ces références après sauvegarde.
