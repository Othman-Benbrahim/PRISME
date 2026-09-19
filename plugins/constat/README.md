# Constat intégré à PRISME

**Ouvrir PRISME, puis cliquer sur Constat dans sa barre d’outils.** Aucune extension,
aucune connexion entre applications et aucune clé d’agent à configurer.
Le modèle utilisé est celui des paramètres PRISME. Le plugin Calibration reste distinct.

## Ce qui est repris de Constat

Source : `Othman-Benbrahim/constat`, commit `be3146d67262bdf83bdbc81a595a1eddb8ff080c`,
licence AGPL-3.0 conservée dans `LICENSE`. Les modules de dossiers, extraction,
empreintes, regroupement, silences, relevés, cotation, prompts, étapes et rapports
sont repris ; l’interface de rendu est adaptée. Les consignes et les validateurs
sont séparés en fichiers de moins de 20 000 caractères, sans changer leurs règles.
Les 11 références méthodologiques originales sont conservées.

La structure garde trois parties : `web/core/` pour la méthode déterministe,
`web/vue/` pour le rendu, `__init__.py` et `stockage.py` pour les services PRISME.
`web/app.js` orchestre les gestes de l’auteur. L’espace est affiché dans une fenêtre
intégrée ; son document HTML isolé évite les conflits de styles avec l’éditeur.

## Parcours

1. Créer un dossier : question, périmètre, horizon de l’étude, décision à éclairer.
2. Ajouter des copies de notes du vault principal, du texte saisi ou un fichier
   HTML enregistré avec son URL d’origine. Rien n’est modifié dans les notes sources.
   Sans balisage ou date déclarée, les métadonnées restent inconnues ; les absences
   mesurées portent sur le contenu importé, pas sur toute la page d’origine.
3. Coter les sources à la main, avec un motif, puis établir le relevé déterministe.
4. Préparer une étape : l’interface montre le modèle, le volume et les messages.
   Cliquer sur « Lancer cette analyse » déclenche un seul appel. Les textes du
   corpus, les références utiles et les sorties préalables validées sont inclus.
5. Relire la sortie, ses rejets et sa trace. Une correction JSON crée une révision
   distincte, non validée. Valider une étape complète ouvre ses étapes dépendantes.
   Une nouvelle révision du parent rend ses descendants obsolètes.
6. Depuis une ACH complète validée, « Verser comme prédiction dans PRISME ».
   L’auteur saisit probabilité, date butoir, condition de résolution ; ces champs
   commencent vides. La proposition rejoint la file de validation PRISME.
7. Dans « Prédictions et Calibration », relire et accepter la proposition, puis
   confirmer séparément sa copie avec ses pièces. Calibration reste facultatif et
   calcule les scores après résolution observée.
8. Exporter le rapport Markdown dans `Rapports/`, ou télécharger le dossier JSON
   complet avec les textes, les prompts, les révisions et les validations.

L’étape 6 (assemblage analytique) est effectuée à l’export, sans appel de modèle,
comme dans Constat. Les étapes 4, 5, 7, 8, 9, 10 et 11 sont proposées séparément.
Une réponse non JSON est conservée comme trace, jamais transformée en analyse validée.
Aucun coût en euros n’est inventé : le volume envoyé et le plafond de sortie sont
annoncés ; le prix dépend du fournisseur configuré.

## Données et limites

Les dossiers sont conservés dans le profil PRISME, sous `plugins/constat/`, dans
une base SQLite distincte pour chaque chemin de vault. Ils ne résident pas dans le
stockage Firefox. Changer de navigateur conserve les dossiers ; changer de vault
change d’espace. Déplacer le vault change sa clé d’espace : exporter/restaurer les
JSON complets permet de reprendre les dossiers à leur nouvel emplacement.
Une révision optimiste empêche deux panneaux d’écraser silencieusement leurs changements.
Après conflit, recharger les dossiers avant de reprendre. Une coupure après dépôt
ou export peut laisser le résultat créé sans trace locale : vérifier la file/le vault
avant de recommencer. Aucun renvoi automatique.

Le journal est append-only dans les opérations de l’application, pas inviolable.
Le fichier du profil et les exports ne sont pas chiffrés. Aucun secret PRISME n’y
est copié ; les textes, prompts et analyses font partie du dossier.
Limites : 20 Mio de données par espace, 2 Mio par fichier importé, 180 000 caractères
par appel de modèle. Un dépassement est refusé, jamais tronqué silencieusement.

La fermeture d’un dossier est réversible. Un dossier clos reste exportable en JSON
et restaurable ; le rapport Markdown nécessite sa réouverture et un relevé à jour.
Une restauration JSON crée un nouvel identifiant et conserve les traces historiques.
Les exports de l’ancienne extension sans corps des sources ne sont pas présentés
comme des sauvegardes complètes. Aucune reprise automatique de Firefox.

Les fonctions liées à la navigation Firefox (capture d’onglet, menus contextuels)
et la recherche Exa de l’extension ne sont pas portées dans cet espace. Les entrées
ici sont les notes PRISME, le texte et le HTML enregistré. Aucune dépendance Node
n’est nécessaire à l’exécution : Node et linkedom servent uniquement aux tests.

## Tester sans modèle

Cliquer sur **Créer un dossier de démonstration**. Il comporte trois documents
explicitement fictifs et une ACH complète **non validée**, sans appel réseau.
Valider l’étape 5, ouvrir une hypothèse, formuler le pari et le déposer. Aucun objet
ne doit apparaître dans le vault avant acceptation dans la file PRISME.

Tests : `npm ci --prefix plugins/constat --ignore-scripts --no-audit --no-fund`,
puis `npm test --prefix plugins/constat` ; Python : `python -m unittest discover -s tests`.
Le plafond de taille inclut tous les fichiers HTML, JS et CSS de cet espace.

## Passages et révisions

Les preuves ACH et la lecture factuelle peuvent porter des citations exactes,
attachées à une version du corps de source. Les contradictions entre preuves
sont déclarées, expliquées et relues. Une correction motivée ajoute une révision
non validée ; l'historique complet reste consultable. Le serveur impose les ajouts
au journal, sans prétendre protéger la base contre une modification manuelle.
Le [guide complet](../../guides-plugins/constat.md) décrit les formulaires, le JSON
et le parcours de transfert avec conservation des pièces.
