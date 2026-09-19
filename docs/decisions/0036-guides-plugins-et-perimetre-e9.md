# 0036 · Guides des plugins et périmètre d'E9

- **Statut** : acceptée ; documentation livrée avant la construction Windows
- **Écrite** : 2026-09-19

## Problème

Les plugins proposent des usages dont les étapes ne sont pas toujours évidentes :
préparer un modèle ne l'active pas pour la recherche ; valider une ACH ne crée pas
une prédiction ; accepter un pari ne l'inscrit pas dans Calibration. Certaines
notices techniques héritées de Second Brain ne décrivent plus le parcours actuel.

L'auteur précise aussi qu'E9 doit désormais porter uniquement sur l'application
Windows et sa release, précédée d'une étape de guides, avec sa propre PR et sa fusion.

## Décision

Créer `guides-plugins/`, séparé du code des plugins, avec un sommaire et un guide
Markdown pour chacun des neuf plugins livrés. Décrire les prérequis, les gestes
réels de l'interface, un premier exemple, l'interprétation des résultats, les données
et leur conservation, ainsi que le dépannage. Les guides complexes détaillent les
validations et dépendances entre étapes. Ils restent consultables dans GitHub.

Cette étape ne modifie pas le fonctionnement de l'application. Elle précède E9.

E9 construira une distribution Windows : `PRISME.exe`, un dossier `plugins/`
contenant tous les plugins fournis, et le dossier `guides-plugins/`, réunis dans
une archive de release. Le code des plugins restera externe à l'exécutable ;
l'application devra fonctionner avec le seul cœur si ce dossier est absent.
Les dépendances nécessaires aux plugins devront être livrées et vérifiées pour
éviter une installation manuelle par l'utilisateur final.

Cette clarification remplace le périmètre ancien d'E9 concernant l'import d'un
vault V1 et le guide de migration. Elle ne vaut pas démarrage de la compilation.
La technique de gel des dépendances décrite en 0030 reste à vérifier sur Windows ;
ces dépendances ne doivent pas être confondues avec le code des plugins externes.

## Écarté

- Un seul guide global qui laisse implicites les gestes propres à chaque plugin.
- Présenter les notices historiques ou les descriptions des manifests comme une
  preuve du fonctionnement actuel sans examiner le code et les écrans.
- Présenter une recherche tierce comme disponible ou fiable sans réserve, un
  classement ACH comme une probabilité, ou une mesure OSINT comme une calibration.
- Commencer la compilation dans cette PR de documentation.
