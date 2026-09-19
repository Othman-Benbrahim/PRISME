# Constat — constituer un dossier et confronter des hypothèses

[Retour aux guides](README.md)

## Comprendre le parcours

**Constat** s'ouvre directement dans PRISME. Aucune extension Firefox, clé d'agent
ou connexion entre deux applications n'est requise. Son dossier rassemble une
question, des copies de sources, des cotations, un relevé et des analyses révisables.

Trois opérations doivent rester distinctes :

- le **relevé déterministe** décrit et compte le corpus importé, sans IA ;
- les **analyses du modèle** proposent des interprétations, à relire et valider ;
- la **prédiction** est votre pari explicite, soumis ensuite à la file PRISME.

L'ACH (*analyse des hypothèses concurrentes*) compare des hypothèses aux éléments
du dossier. Son classement ne fournit pas une probabilité. [Calibration](calibration.md)
est le plugin qui évaluera ensuite vos paris, après observation des résultats.

## Premier essai sans modèle

Utilisez un vault d'essai pour conserver les données fictives à part.

1. Cliquez sur **Constat**, puis **Créer un dossier de démonstration**.
2. Examinez les trois documents fictifs, leur relevé et l'ACH préparée. La
   démonstration ne lance aucun appel IA et son ACH n'est pas encore validée.
3. Ouvrez l'analyse de l'étape 5, relisez-la, puis cliquez sur **Valider l'étape 5**.
4. Sur une hypothèse, choisissez **Verser comme prédiction dans PRISME**.
5. Remplissez le pari : événement observable, probabilité entre 0 et 1, date
   butoir future et condition permettant de décider oui ou non. Le domaine est facultatif.
6. Cliquez sur **Déposer dans la file de validation PRISME**.
7. Dans **Prédictions et Calibration**, cliquez sur **Actualiser les prédictions de
   ce dossier**. Relisez l'énoncé, la probabilité, l'échéance et les conditions,
   puis **J’ai relu : accepter cette prédiction**. Cette action crée la fiche E11.
8. Dépliez **Relire les pièces qui accompagneront le pari**, indiquez les bornes
   de l'horloge du monde si elles sont connues, puis **Confirmer la copie du pari
   et de ses pièces dans Calibration**. Cette seconde action fige la référence.
9. Après une observation réelle, résolvez la fiche Prédiction dans PRISME puis
   actualisez Calibration. [Son guide](calibration.md) explique les scores.

La validation de l'ACH ne vaut pas acceptation automatique de la prédiction.
Les champs de probabilité, d'échéance et de condition commencent volontairement vides.

## Créer un vrai dossier

Cliquez sur **Nouveau dossier** et remplissez les quatre champs :

| Champ | Exemple de formulation |
|---|---|
| Question | « Quels indices permettent de juger si notre fournisseur livrera avant la date prévue ? » |
| Périmètre | Produit concerné, zone, acteurs et sources examinées |
| Horizon de l'étude | Période couverte par l'analyse |
| Décision à éclairer | Décider d'un stock de sécurité ou d'un fournisseur alternatif |

L'horizon de l'étude est un texte de cadrage. Il ne remplit pas automatiquement la
date butoir d'une future prédiction.

Dans **Ajouter des sources au corpus**, choisissez :

- **Importer une copie de la note** : copie une note du vault principal ; elle
  n'est pas modifiée et ses éditions futures ne mettent pas la copie à jour ;
- **Verser le texte** : texte saisi ou collé, avec titre, URL, éditeur et date
  déclarée lorsqu'ils sont connus ;
- **Extraire et importer le HTML** : fichier HTML enregistré et URL d'origine.

Le plugin ne capture aucun onglet et n'effectue pas la recherche Exa de l'extension
historique. Les métadonnées absentes restent inconnues. Un texte copié peut avoir
perdu les liens, images, dates ou autres éléments de sa page d'origine.

## Coter puis établir le relevé

Dans chaque bloc **Coter…**, choisissez la fiabilité de la source et la crédibilité
de l'information, puis saisissez le motif et cliquez sur **Enregistrer la cotation**.

| Fiabilité | Signification | Crédibilité | Signification |
|---|---|---|---|
| A | complètement fiable | 1 | confirmée par d'autres sources |
| B | généralement fiable | 2 | probablement vraie |
| C | assez fiable | 3 | possiblement vraie |
| D | pas habituellement fiable | 4 | douteuse |
| E | non fiable | 5 | improbable |
| F | fiabilité non évaluable | 6 | véracité non évaluable |

**F et 6 sont des abstentions, pas les plus mauvaises notes.** Les cotations sont
vos appréciations justifiées, pas des notes attribuées automatiquement par l'IA.
Une source non cotée peut rester non cotée.

Cliquez sur **Établir le relevé déterministe**. Relisez les regroupements,
corroborations et absences signalées. Des textes proches peuvent être des reprises
d'une même source ; une absence détectée porte seulement sur le contenu importé.
Un relevé peut être utile et complet sans aucun appel de modèle.

## Analyser et valider par étapes

Configurez l'IA dans PRISME pour utiliser cette partie. Les boutons disponibles
dépendent d'un relevé à jour et des étapes préalables validées.

| Étape | Travail proposé | Préalable analytique |
|---|---|---|
| 4 | Analyse triple | Aucun autre résultat d'étape requis |
| 5 | Hypothèses concurrentes (ACH) | Aucun autre résultat d'étape requis |
| 7 | Scénarios prospectifs | Étape 5 validée |
| 8 | Évaluation du risque | Étape 7 validée |
| 9 | Recommandations actionnables | Étape 8 validée |
| 10 | Contrôle des biais | Étapes 5 et 7 validées |
| 11 | Boucle de rétroaction | Aucun autre résultat d'étape requis |

Les étapes 1 à 3 correspondent au cadrage, à la cotation et au relevé. L'étape 6
est assemblée lors de l'export du rapport, sans appel IA supplémentaire.

Pour chaque analyse :

1. Choisissez l'étape et ouvrez **Voir les messages envoyés au modèle**.
2. Vérifiez le modèle, le volume, le corpus et les consignes. **Annuler** à ce
   stade abandonne la préparation sans appel.
3. Cliquez sur **Lancer cette analyse** pour un appel explicite.
4. Examinez la sortie, les éléments écartés et la réponse brute. Une sortie JSON
   invalide ou incomplète ne doit pas être considérée comme validée.
5. Si nécessaire, modifiez la **Révision JSON de l'analyse**, expliquez le motif, puis cliquez sur
   **Enregistrer ma révision**. Cela conserve l'ancienne trace et crée une nouvelle
   révision, encore à valider.
6. Validez seulement une sortie complète que vous avez relue.

L'ACH utilise des cases **C** (compatible), **I** (incompatible) et **N** (neutre).
Le classement privilégie le moins d'incompatibilités, puis le plus de compatibilités.
Les cases manquantes ne sont pas transformées en N. Les rôles et références exigés
sont indiqués dans les rejets et dans les messages préparés : ne supprimez pas
arbitrairement des champs du JSON pour faire disparaître un avertissement.

Si vous ajoutez une source ou changez sa cotation, le relevé devient historique :
recalculez-le et réexaminez les analyses. Une nouvelle révision d'une étape parent
rend aussi ses descendants obsolètes. Leur ancienne validation ne suffit plus.

## Relier les affirmations aux passages sources

Sous l'ACH, **Passages sources et contradictions** montre les extraits cités,
leur source, leur empreinte SHA-256 et leur position dans le texte conservé.
La lecture factuelle de l'étape 4 peut également porter des passages. Un extrait
atteste ce que dit le document ; il ne prouve pas à lui seul que cela est vrai.
Les anciennes analyses sans extraits restent lisibles avec un avertissement explicite.

1. Ouvrez **Relier une preuve à un passage exact**.
2. Choisissez la preuve ACH et sa source. Copiez l'extrait depuis le texte affiché.
3. Collez-le sans reformulation. Si le même extrait apparaît plusieurs fois,
   précisez sa position de début (unités UTF-16, à partir de zéro) ou choisissez
   un passage plus long et unique.
4. Expliquez pourquoi vous ajoutez ce passage, puis enregistrez.
5. Relisez et validez la **nouvelle** révision avant de proposer une prédiction.

Un passage inexistant ou tiré d'une autre version de la source rend la sortie
incomplète. Le texte brut du modèle reste visible dans la trace. Pour retirer ou
remplacer un passage erroné, utilisez la révision JSON de l'étape, avec un motif.
Exemple d'ajout dans une preuve :

```json
"passages": [{"source": "s-001", "extrait": "Phrase copiée exactement."}]
```

**Signaler une contradiction entre deux preuves** conserve leurs identifiants et
votre explication dans une nouvelle révision. Cela ne tranche pas automatiquement
le désaccord. Dans le JSON, la liste `contradictions` contient des objets
`{"a":"P1","b":"P2","motif":"Explication"}`. Retirer un signalement exige aussi une
correction motivée. La matrice ACH conserve séparément ses cases incompatibles
avec une hypothèse : ces deux notions ne sont pas interchangeables.

**Historique complet des analyses, corrections et validations** permet de revoir
les anciennes sorties, leurs auteurs ou modèles, les motifs et les dates de
validation. Le serveur refuse de réécrire le journal par l'interface. Une personne
qui modifie directement le fichier SQLite peut toujours l'altérer : ce n'est pas
un journal certifié.

## Transférer les preuves avec le pari

Le dépôt de la proposition crée aussi une note de pièces dans `Rapports/` :
hypothèse, éléments compatibles et incompatibles, citations, versions des sources,
contradictions et historique des validations. La fiche Prédiction garde le lien.
Calibration copie ensuite le contenu de cette note dans sa référence datée.
Après copie, déplacer ou supprimer la note d'origine n'efface pas ces pièces.

Si le pari ou ses pièces changent depuis votre relecture, l'inscription est refusée :
actualisez et relisez avant de confirmer. Une limite de 200 ko s'applique au rapport
de pièces (210 ko avec sa provenance) ; aucun extrait n'est tronqué silencieusement.

Constat reste utilisable si Calibration est désactivé ou absent. Le panneau indique
alors comment poursuivre après activation. Les anciennes propositions sans note de
pièces peuvent être copiées, mais leurs preuves manquantes ne sont pas reconstituées.
Une restauration JSON crée un nouveau dossier : ses anciens transferts restent des
traces historiques et ne déclenchent aucune nouvelle inscription.

Après une coupure, **Actualiser les prédictions de ce dossier** retrouve les
propositions et fiches existantes même si leur dernière trace locale a échoué.
Vérifiez aussi `Rapports/` : une note de pièces peut avoir été créée avant un échec
de dépôt. Aucun renvoi ni résolution automatique n'est effectué.

## Exporter, sauvegarder et reprendre

- **Enregistrer le rapport dans le vault** crée un Markdown dans `Rapports/`, avec
  provenance. Le dossier doit être ouvert et son relevé à jour. Relisez le statut
  des analyses : exporter n'est pas les valider.
- **Télécharger le dossier complet** exporte un JSON contenant les textes et les
  traces. C'est le format de reprise du dossier, distinct du rapport de lecture.
- **Importer comme nouveau dossier** restaure ce JSON sous un nouvel identifiant,
  sans écraser le dossier d'origine.
- **Clore le dossier** le conserve ; **Restaurer le dossier** le rouvre.

Les dossiers résident dans le profil PRISME, sous `plugins/constat/`, avec une base
SQLite distincte pour chaque chemin de vault. Changer de navigateur ne les efface
pas ; déplacer le vault change son espace. Exportez les JSON complets avant un
déplacement. Les anciens exports Firefox ne sont pas repris automatiquement.

Les dossiers et exports ne sont pas chiffrés. Les textes, prompts et réponses
font partie des données. Un appel d'analyse envoie les éléments affichés au
fournisseur IA configuré ; le relevé et le dossier de démonstration restent locaux.

## Dépannage

| Symptôme | Que faire ? |
|---|---|
| Étape grisée | Vérifier le modèle, l'ouverture du dossier, le relevé et les préalables validés |
| « Relevé historique » | Recalculer le relevé après les changements de corpus ou de cotation |
| Pas de versement de prédiction | Obtenir une ACH actuelle, complète et validée |
| Réponse non JSON ou incomplète | Lire la trace et les rejets ; corriger une révision ou relancer l'étape |
| Conflit entre deux panneaux | **Recharger les dossiers**, puis reprendre sur l'état actualisé |
| Résultat incertain après une coupure | Vérifier la file PRISME ou `Rapports/` avant de recommencer un dépôt/export |
| Import ou analyse trop volumineux | Respecter 2 Mio pour un HTML importé, 20 Mio par espace et 180 000 caractères par appel IA |

**Repère de réussite :** les sources et cotations restent traçables, chaque étape
est relue séparément, et aucune proposition de prédiction n'entre dans le vault
avant son acceptation dans PRISME.
