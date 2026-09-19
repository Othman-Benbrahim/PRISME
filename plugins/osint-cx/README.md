> **PRISME :** le [guide utilisateur actuel](../../guides-plugins/osint-cx.md)
> décrit les écrans, la configuration et les seuils du code actuel. Les sections
> Second Brain ci-dessous sont conservées comme historique et ne constituent plus
> le parcours d’installation ou d’utilisation de PRISME.

# OSINT Cross-Reference — Plugin Second Brain

Plugin OSINT défensif pour **Second Brain** permettant de regrouper plusieurs recherches publiques ou configurées autour d’un identifiant : pseudo, email, téléphone, IP, domaine, entreprise, profil social ou URL LinkedIn.

L’objectif du plugin est de faciliter un **audit d’exposition numérique** : vérifier quelles informations publiques, semi-publiques ou issues d’API configurées sont associées à un identifiant, sans conclure automatiquement à une identité certaine.

Le plugin privilégie une approche de **corrélation prudente** : il compare plusieurs signaux, affiche les sources consultées et génère un score indicatif, mais ne doit jamais être utilisé comme preuve d’identification.

---

## Fonctionnalités principales

Le plugin permet de lancer des recherches sur plusieurs sources :

* recherche statique de pseudos sur plusieurs plateformes ;
* recherche email : Gravatar, DNS, domaines associés ;
* recherche téléphone : analyse d’indicatif ;
* recherche IP : géolocalisation approximative via `ipapi.co` ;
* recherche domaine : DNS et RDAP ;
* API Entreprises françaises ;
* Reddit public ;
* GitHub public ;
* Wikidata ;
* Maigret / Sherlock en local si installé ;
* LinkedIn via RapidAPI si une API compatible est configurée ;
* score de corrélation multi-sources.

---

## Structure du plugin

```txt
osint-cx/
├── manifest.json
├── __init__.py
├── ui.html
├── ui.css
├── ui.js
└── README.md
```

Le fichier `__init__.py` expose les routes Flask du plugin via la fonction :

```python
register(app, rd_cfg)
```

L’interface est injectée dans Second Brain via les fichiers :

```txt
ui.html
ui.css
ui.js
```

---

## Installation

Placer le dossier du plugin ici :

```txt
Second-Brain/plugins/osint-cx/
```

Puis relancer l’application :

```bash
python second_brain.py
```

---

## Variables d’environnement

> **PRISME** : les clés `X_BEARER_TOKEN` et `RAPIDAPI_KEY` se saisissent de préférence dans PRISME (bouton 🧩 Plugins > OSINT Cross-Reference > Secrets), où elles sont chiffrées sous Windows. Le fichier `.env` reste lu en secours ; les autres réglages (URL, hôte RapidAPI…) restent dans `.env`.


Le plugin fonctionne en grande partie sans clé API.

Certaines fonctionnalités avancées nécessitent cependant des variables dans le fichier `.env` situé à la racine de Second Brain.

Exemple :

```env

# X API, optionnel
X_BEARER_TOKEN=votre_bearer_token_x
X_BASE_URL=https://api.x.com

# LinkedIn via RapidAPI
RAPIDAPI_KEY=votre_cle_rapidapi
LINKEDIN_RAPIDAPI_HOST=linkedin-api8.p.rapidapi.com
LINKEDIN_RAPIDAPI_ENDPOINT=/get-profile-data-by-url
LINKEDIN_RAPIDAPI_METHOD=GET
LINKEDIN_RAPIDAPI_PARAM=url

# Maigret / Sherlock
OSINTCX_CLI_TIMEOUT=120
```

Ne jamais publier le fichier `.env` sur GitHub.

Ajouter dans `.gitignore` :

```gitignore
.env
```

---

## Configuration LinkedIn via RapidAPI

Le plugin peut interroger une API LinkedIn disponible sur RapidAPI.

RapidAPI n’est pas une API unique : chaque API possède son propre `host`, son propre endpoint et son propre format. Il faut donc configurer les variables suivantes dans `.env`.

```env
RAPIDAPI_KEY=votre_cle_rapidapi
LINKEDIN_RAPIDAPI_HOST=le-host-de-votre-api.p.rapidapi.com
LINKEDIN_RAPIDAPI_ENDPOINT=/endpoint/de/profil
LINKEDIN_RAPIDAPI_METHOD=GET
LINKEDIN_RAPIDAPI_PARAM=url
```

Exemple :

```env
RAPIDAPI_KEY=xxxxxxxxxxxxxxxx
LINKEDIN_RAPIDAPI_HOST=linkedin-api8.p.rapidapi.com
LINKEDIN_RAPIDAPI_ENDPOINT=/get-profile-data-by-url
LINKEDIN_RAPIDAPI_METHOD=GET
LINKEDIN_RAPIDAPI_PARAM=url
```

La valeur `LINKEDIN_RAPIDAPI_HOST` correspond à l’en-tête RapidAPI :

```txt
X-RapidAPI-Host
```

Elle est visible dans les exemples de code fournis sur la page RapidAPI de l’API choisie.

Le plugin permet ensuite de fournir une URL LinkedIn du type :

```txt
https://www.linkedin.com/in/username/
```

Les informations récupérées peuvent être utilisées dans le score de corrélation :

* nom complet ;
* titre ou headline ;
* localisation ;
* entreprise actuelle ;
* résumé ;
* URL du profil.

---

## Maigret / Sherlock

Le plugin peut appeler Maigret ou Sherlock pour enrichir les recherches de pseudos.

Installation recommandée dans le même environnement Python que Second Brain :

```bash
python -m pip install maigret
```

ou :

```bash
python -m pip install sherlock-project
```

Sous Windows, si la commande `maigret` n’est pas trouvée dans le `PATH`, le plugin tente aussi un appel via :

```bash
python -m maigret
```

Maigret peut être lent. Il est recommandé d’augmenter le timeout si nécessaire :

```env
OSINTCX_CLI_TIMEOUT=120
```

---

## Sources sans clé API

Certaines sources fonctionnent sans clé :

### API Entreprises françaises

Permet de rechercher des entreprises, établissements, dirigeants ou informations publiques associées à un terme.

Route plugin :

```txt
GET /api/plugins/osint-cx/entreprise?q=<terme>
```

### Reddit public

Permet de récupérer des informations publiques basiques sur un utilisateur Reddit.

Route plugin :

```txt
GET /api/plugins/osint-cx/reddit?q=<username>
```

### GitHub public

Permet de récupérer les informations publiques d’un profil GitHub :

* nom affiché ;
* bio ;
* localisation ;
* entreprise ;
* blog ou site web ;
* nombre de repositories publics ;
* avatar.

Route plugin :

```txt
GET /api/plugins/osint-cx/github?q=<username>
```

### Wikidata

Permet de rechercher des entités publiques : personnes publiques, organisations, entreprises, projets, lieux, etc.

Route plugin :

```txt
GET /api/plugins/osint-cx/wikidata?q=<terme>
```

---

## Routes principales

```txt
GET  /api/plugins/osint-cx/username?q=<pseudo>
GET  /api/plugins/osint-cx/email?q=<email>
GET  /api/plugins/osint-cx/phone?q=<telephone>
GET  /api/plugins/osint-cx/ip?q=<ip>
GET  /api/plugins/osint-cx/domain?q=<domaine>

GET  /api/plugins/osint-cx/entreprise?q=<terme>
GET  /api/plugins/osint-cx/reddit?q=<username>
GET  /api/plugins/osint-cx/github?q=<username>
GET  /api/plugins/osint-cx/wikidata?q=<terme>
GET  /api/plugins/osint-cx/social-cli?q=<username>&tool=auto

GET  /api/plugins/osint-cx/linkedin?q=<username>&url=<url_linkedin>
POST /api/plugins/osint-cx/linkedin

POST /api/plugins/osint-cx/score
```

---

## Score de corrélation

Le score de corrélation est un indicateur de concordance entre plusieurs sources.

Il prend en compte, selon les données disponibles :

* pseudo identique ;
* nom affiché proche ;
* localisation similaire ;
* entreprise ou organisation commune ;
* site web ou domaine commun ;
* présence sur plusieurs plateformes ;
* signaux GitHub ;
* signaux Wikidata ;
* signaux LinkedIn ;

Le score est affiché comme un **indice**, pas comme une preuve.

Niveaux indicatifs :

```txt
0–39   : concordance faible
40–69  : concordance moyenne
70–100 : concordance forte
```

Exemple d’interprétation :

```txt
Score faible :
Les sources ne permettent pas de relier clairement les informations.

Score moyen :
Plusieurs signaux concordent, mais une vérification manuelle reste nécessaire.

Score fort :
Plusieurs sources indépendantes présentent des éléments cohérents, mais cela ne constitue pas une preuve définitive.
```

---

## Présentation des résultats

Le plugin affiche les résultats sous forme de cartes lisibles, plutôt qu’en JSON brut.

Les blocs peuvent inclure :

* titre de la source ;
* état de la recherche ;
* résultats principaux ;
* badges de sources ;
* métadonnées ;
* score de confiance ;
* avertissements en cas d’erreur ou de quota dépassé.

Le JSON reste utilisé uniquement en interne pour les échanges entre le frontend et le backend.

---

## Usage recommandé

Ce plugin doit être utilisé pour :

* auditer ses propres identifiants ;
* vérifier l’exposition publique d’un email, pseudo ou domaine ;
* analyser des comptes ou données avec consentement ;
* documenter les sources consultées ;
* comparer plusieurs signaux publics sans conclusion automatique ;
* aider à comprendre l’empreinte numérique d’une personne, d’une entreprise ou d’un projet dans un cadre légitime.

---

## Limites

Le plugin ne garantit pas l’exactitude des informations retournées.

Certaines sources peuvent être :

* incomplètes ;
* obsolètes ;
* temporairement indisponibles ;
* limitées par des quotas ;
* sujettes à des homonymies ;
* bloquées par des protections anti-abus ;
* dépendantes d’APIs tierces instables.

Les résultats doivent toujours être vérifiés manuellement.

---

## Sécurité

Les clés API doivent rester côté serveur dans le fichier `.env`.

Ne jamais placer de clé dans :

```txt
ui.js
ui.html
manifest.json
README.md
```

Ne jamais envoyer `.env` sur GitHub.

---

## Note éthique

Ce plugin est conçu pour un usage défensif et responsable.

Il ne doit pas être utilisé pour harceler, surveiller, désanonymiser ou cibler une personne sans base légitime ou consentement.

Le score de corrélation ne doit jamais être interprété comme une identification certaine.

Le plugin fournit des indices, pas des certitudes.
