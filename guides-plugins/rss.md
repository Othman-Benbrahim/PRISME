# RSS — organiser une veille et comparer les articles

[Retour aux guides](README.md)

## À quoi sert ce plugin ?

Le bouton **RSS** gère une liste de flux RSS/Atom, récupère leurs articles et lance
une analyse IA sur votre sélection. Il peut aussi calculer localement des signaux
lexicaux pour étayer la synthèse. La récupération est déclenchée par vos actions :
ce parcours n'est pas une surveillance programmée en arrière-plan.

## Ajouter ses flux

1. Ouvrez **RSS → Mes flux**.
2. Saisissez l'URL d'un flux, ou la page d'accueil du site pour tenter une
   découverte automatique. L'URL directe du flux est préférable si la découverte échoue.
3. Ajoutez éventuellement des tags, par exemple `#recherche #numerique`.
4. Cliquez sur **Ajouter**, puis vérifiez le titre et l'URL effectivement retenus.
5. Commencez avec un ou deux flux. **Recharger** relit la liste enregistrée.

Ajouter un flux nécessite de joindre son serveur, mais pas d'appeler une IA.
Les flux sont conservés dans **`flux-rss.md` à la racine du vault principal**.
Vous pouvez y organiser les entrées avec des titres `##` et des lignes de la forme
`- [Nom du flux](URL-du-flux) #tag`. Remplacez `URL-du-flux` par une URL réelle.

L'ajout ou la suppression depuis l'interface réécrit ce fichier à partir des flux
reconnus. N'y stockez pas des notes libres à préserver : les autres paragraphes
peuvent disparaître lors de cette réécriture. Supprimer un flux de la liste ne
supprime pas les synthèses déjà enregistrées.

## Première analyse

1. Configurez et testez l'IA dans les paramètres PRISME.
2. Dans **RSS → Analyser**, cochez les flux voulus.
3. Choisissez une fenêtre temporelle : 24 heures, 7 jours, 30 jours ou aucun filtre.
4. Limitez le nombre d'articles par flux ; **5** suffit pour un premier essai.
5. Choisissez les options et le mode décrits ci-dessous.
6. Posez une question précise : « Quels événements nouveaux sont décrits et sur
   quels points les sources divergent-elles ? Cite les articles concernés. »
7. Renseignez éventuellement un **Prompt système**, ou choisissez un preset de
   [Prompts Manager](prompts.md).
8. Cliquez sur **Analyser**, examinez les erreurs de récupération et la synthèse,
   puis **Sauver comme .md** si vous souhaitez la conserver.

## Choisir les options

| Réglage | Effet et limite |
|---|---|
| Fetch contenu complet | Tente de lire les pages des articles ; une page inaccessible peut rester représentée par sa description RSS |
| Signaux faibles (analyse locale) | Calcule des fréquences, associations de mots et évolutions lexicales, puis les fournit à l'IA |
| Tous les flux ensemble | Produit une synthèse commune, utile pour comparer les thèmes |
| Flux par flux | Traite séparément les flux ayant des articles ; multiplie les appels IA et les sections de résultat |

« Contenu complet » désigne une extraction, pas une archive intégrale : la lecture
est plafonnée à 5 000 caractères par article, puis le texte peut encore être réduit
pour construire le message IA. Les flux eux-mêmes ne fournissent généralement
qu'une partie des publications passées : choisir « Tout » ne récupère pas toute
l'histoire du site.

Un article dont la date est inconnue est conservé même avec un filtre temporel.
Vérifiez les dates au lieu de considérer la sélection comme une période garantie.

## Interpréter les signaux et les erreurs

Une hausse de fréquence est un fait sur **le corpus récupéré**, pas une prédiction
ni une preuve d'importance. Un même article repris par plusieurs flux peut peser
plusieurs fois dans l'analyse. Une absence de mot ne prouve pas une absence
d'événement. Le score de [Calibration](calibration.md) mesure autre chose.

Le bouton d'annulation ou la fermeture coupe l'attente dans le navigateur ; cela
ne garantit pas qu'un appel déjà reçu par le fournisseur IA soit arrêté ou non facturé.
Évitez de relancer immédiatement une grosse analyse sans examiner son état.

## Données et sauvegarde

Les sites reçoivent les demandes de flux et de pages. Le fournisseur IA reçoit les
textes ou extraits récupérés, vos consignes et les signaux calculés lorsqu'ils sont
activés. Une analyse locale des mots ne rend pas la synthèse IA locale.

**Sauver comme .md** crée une note de veille dans le dossier courant du vault,
avec le résultat et la provenance. Elle ne constitue pas une sauvegarde complète
des pages consultées. Conservez séparément les originaux nécessaires à votre dossier.

| Symptôme | Que faire ? |
|---|---|
| Flux introuvable | Fournir l'URL RSS/Atom directe plutôt que la page d'accueil |
| Aucun article | Élargir la fenêtre, vérifier les cases et le flux d'origine |
| Une partie des flux échoue | Lire les erreurs par source ; réduire la sélection pour isoler le problème |
| Analyse très lente | Diminuer les flux et articles, ou désactiver la récupération des pages |
| Anciennes dates dans le résultat | Contrôler les articles sans date reconnue |

**Repère de réussite :** la liste des flux persiste, la sélection récupère des
articles identifiables, et la synthèse enregistrée peut être confrontée à leurs sources.
