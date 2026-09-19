# Context Builder — interroger plusieurs notes choisies

[Retour aux guides](README.md)

## À quoi sert ce plugin ?

Le bouton **Multi-sélection** assemble plusieurs notes, puis envoie ce corpus avec
votre question au modèle configuré. Il convient à une comparaison de comptes rendus,
à une synthèse de dossier ou à la recherche de contradictions entre notes connues.

Vous choisissez les documents. Aucun modèle d'embeddings n'est nécessaire ; il
ne s'agit pas d'une recherche automatique de passages dans tout le vault.

## Préparer et sélectionner

1. Enregistrez vos modifications : le corpus est lu depuis les fichiers sur disque,
   pas depuis les changements encore non sauvegardés dans l'éditeur.
2. Placez-vous dans le dossier du vault à explorer, puis ouvrez **Multi-sélection**.
3. Filtrez les noms et cochez deux ou trois notes. **Ouvert** sélectionne la note
   active ; **Aucun** vide la sélection. Vérifiez les cases et le compteur.
4. Choisissez le mode :

| Mode | Contenu ajouté |
|---|---|
| Manuel | Uniquement les notes cochées |
| Auto | Notes cochées, puis notes atteintes par leurs `[[liens]]`, jusqu'à la profondeur choisie |

En mode Auto, une profondeur de 1 suit les liens directs ; 2 suit aussi les liens
trouvés dans ces premières notes, etc. L'interface propose de 1 à 5 niveaux.
Un lien non résolu n'invente pas de document. Les chemins déjà rencontrés ne sont
pas ajoutés à nouveau par le parcours des liens.

## Examiner puis poser une question

1. Cliquez sur **Aperçu corpus**. Un nouvel onglet montre le texte assemblé et les
   fichiers ajoutés par les liens. Cet aperçu ne lance pas d'appel IA.
2. Si l'onglet ne s'ouvre pas, autorisez les fenêtres contextuelles pour PRISME.
3. Saisissez une question : « Compare les décisions de ces trois comptes rendus.
   Pour chaque divergence, cite la note et sépare décision actée et proposition. »
4. Facultativement, renseignez le **Prompt système**, par exemple « Réponds en
   français ; signale explicitement quand le corpus ne permet pas de conclure ».
5. Cliquez sur **Envoyer à l'IA** et relisez la réponse avec les notes d'origine.
6. Cliquez sur **Sauver comme .md**, ou **Nouvelle question** pour un autre examen.

Ce champ de prompt peut recevoir du texte copié depuis [Prompts](prompts.md), mais
il ne dispose pas actuellement du sélecteur automatique de presets.

## Taille du corpus et résultats

L'aperçu montre le corpus assemblé. L'envoi au modèle est limité à **60 000 caractères** ;
le surplus est tronqué et la réponse affiche un avertissement. Le nombre de fichiers
indiqué ne garantit donc pas que chaque fichier ait été envoyé en entier.
Réduisez la sélection ou la profondeur si le corpus est tronqué. Le compteur de
jetons est une estimation, pas une mesure exacte du modèle.

La sauvegarde crée `contexte-…` dans le dossier courant : question, liste de notes,
réponse et provenance de génération. Les documents du corpus ne sont pas remplacés.

## Données envoyées

L'assemblage et l'aperçu sont locaux. Au clic sur **Envoyer à l'IA**, le corpus retenu,
la question et les consignes partent vers le fournisseur configuré. Les notes
ajoutées en mode Auto font partie de cet envoi : inspectez l'aperçu avant de lancer.

## Dépannage

| Symptôme | Que faire ? |
|---|---|
| Liste inattendue | Vérifier le dossier courant et la racine de vault choisie |
| Ancien texte analysé | Enregistrer les notes, puis reconstruire l'aperçu |
| Fichier lié absent | Vérifier le `[[lien]]`, son existence et la profondeur |
| Réponse tronquée ou erreur de contexte | Réduire le corpus et la profondeur |
| Aucun fichier ou question vide | Cocher au moins une note et saisir une question |

**Repère de réussite :** l'aperçu contient les notes voulues, la réponse s'appuie
sur elles, et la sauvegarde crée une note distincte dans le vault.
