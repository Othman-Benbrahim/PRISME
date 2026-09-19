# DDG — recherche web et synthèse sourcée

[Retour aux guides](README.md)

## À quoi sert ce plugin ?

**DDG** construit une requête web depuis la note ouverte. Il affiche les résultats,
peut extraire du texte des pages, puis répond à une question ou produit une synthèse.
La recherche peut utiliser des solutions de repli prévues dans le code si un
accès DuckDuckGo échoue ; le service effectivement utilisé peut donc varier.

## Préparer

Ouvrez une note Markdown, configurez l'IA dans les paramètres PRISME et testez la
connexion. Le plugin utilise Internet pour la recherche et, si vous l'activez,
pour lire les pages. Il ne demande pas de clé DuckDuckGo spécifique.

## Premier parcours

1. Écrivez dans une note un sujet précis, par exemple une comparaison de logiciels
   libres de prise de notes. Évitez d'y inclure des informations personnelles inutiles.
2. Ouvrez **DDG** et renseignez l'indication de recherche.
3. Choisissez le nombre de résultats et l'option de récupération du contenu des
   pages. Commencez avec peu de résultats pour faciliter la relecture.
4. Cliquez sur **Lancer la recherche**. Vérifiez la requête générée et les liens.
5. Pour une réponse ciblée, remplissez **Question / objectif** : « Quels outils
   exportent réellement en Markdown et quelles restrictions sont documentées ? »
6. Le **Prompt système** donne les consignes de réponse. Vous pouvez utiliser
   **Choisir un preset…** si [Prompts Manager](prompts.md) est actif.
7. Cliquez sur **Synthétiser**, puis comparez les citations aux pages d'origine.
8. Cliquez sur **Sauver comme .md** pour conserver le résultat.

L'indication guide la recherche ; la question guide la synthèse. Une bonne requête
ne suffit pas à produire une réponse utile si la question reste imprécise.

## Que signifie « contenu complet » ?

L'option tente de récupérer et d'extraire le texte des premières pages. Ce n'est
pas une archive intégrale : le téléchargement extrait au plus **5 000 caractères**
de texte par page et la synthèse en utilise au plus **3 500** par source. En cas
d'échec, un extrait du moteur, ou *snippet*, peut être utilisé à la place.

L'interface indique combien de pages ont été lues et combien de sources reposent
seulement sur un extrait. Une page dynamique, protégée ou nécessitant une connexion
peut être inutilisable. Le titre d'un lien ne prouve pas que son contenu a été lu.

## Données et sauvegarde

La génération de requête reçoit au plus 4 000 caractères de la note ; la synthèse
utilise un contexte limité à 3 000 caractères, les sources et vos consignes.
Ces données sont envoyées au fournisseur IA configuré. Les moteurs reçoivent la
requête ; les sites sont contactés lorsque la récupération des pages est activée.

**Sauver comme .md** crée une nouvelle note `ddg-…` dans le dossier courant du vault,
avec la requête, la question, la synthèse et les liens. La provenance est indiquée.
Aucune sauvegarde de synthèse n'a lieu avant ce clic ; la note source reste distincte.

## Dépannage et limites

| Symptôme | Vérification |
|---|---|
| Aucun fichier ouvert | Ouvrir une note `.md` avant DDG |
| Échec de l'IA | Tester le service et le modèle dans les paramètres |
| Recherche bloquée | Lire le détail, simplifier la requête proposée et réessayer après un délai |
| Beaucoup de snippets | Ouvrir les sources manuellement ; ne pas présenter l'analyse comme une lecture intégrale |
| Réponse trop générale | Poser une question précise et limiter le corpus aux résultats utiles |
| Sauvegarde indisponible | Attendre qu'une synthèse soit produite |

Le plugin ne démontre pas que deux articles sont indépendants et ne vérifie pas
chaque affirmation de la synthèse. Plusieurs sites peuvent reprendre la même
publication. **Repère de réussite :** vous pouvez rattacher les points principaux
à des liens consultables et retrouver la synthèse dans une nouvelle note.
