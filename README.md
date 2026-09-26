# PRISME

<img width="1916" height="936" alt="Capture d&#39;écran 2026-09-19 211240" src="https://github.com/user-attachments/assets/6704cd92-c114-49a4-a2bf-9962bbe1a44a" />

<img width="1880" height="923" alt="Firefox_Screenshot_2026-09-19T19-13-53 076Z" src="https://github.com/user-attachments/assets/6e779569-870b-42ee-8ed1-a08739e2f93a" />


**Une mémoire personnelle locale pour relier ses sources, structurer ses analyses et suivre ses décisions.**

PRISME est une application open source de gestion de connaissances, construite autour de notes Markdown. Elle réunit un éditeur, la recherche dans les documents, un graphe de liens, l'import de sources, des outils d'intelligence artificielle et des plugins spécialisés dans la veille, l'analyse et l'évaluation des prédictions.

Son objectif est de conserver le chemin entre une information et son utilisation : retrouver la source d'une note, comprendre sur quels éléments repose une hypothèse, distinguer une proposition du modèle d'une validation humaine, puis comparer une prévision à ce qui s'est réellement produit.

> **L'IA propose, l'auteur valide.** Les sources, les hypothèses et les résultats observés gardent des rôles distincts.

**État du projet :** version de développement utilisable depuis les sources. Les neuf plugins et leurs guides sont intégrés. La distribution Windows avec `PRISME.exe` a été construite et intégrée en **E9** (PR #22). Cette branche poursuit Constat ; la publication des releases reste une opération distincte.

[Prise en main](#installation-depuis-les-sources) · [Plugins et guides](#les-neuf-plugins) · [Constat et Calibration](#de-lanalyse-à-la-prédiction) · [Feuille de route](docs/FEUILLE-DE-ROUTE.md)

## À quoi sert PRISME ?

PRISME s'adresse aux personnes qui accumulent des notes, des lectures, des conversations avec des modèles et des analyses, puis souhaitent les retrouver et les exploiter ensemble.

Quelques usages :

- constituer une base de connaissances personnelle, organisée en dossiers et reliée par des liens ;
- importer des conversations ou des documents textuels en conservant leurs références ;
- rechercher un passage précis ou explorer les notes liées à une question ;
- demander une synthèse à un modèle à partir d'un corpus choisi ;
- mener une veille web, scientifique ou RSS ;
- confronter plusieurs hypothèses dans un dossier d'analyse ;
- enregistrer une décision, une tâche ou une prédiction sous une forme structurée ;
- mesurer la qualité de ses probabilités une fois les résultats connus.

## Vos notes restent des fichiers Markdown

Le **vault** est le dossier qui contient vos notes. Les documents du vault restent des fichiers `.md`, lisibles avec un éditeur de texte et compatibles avec les usages Markdown d'Obsidian.

PRISME s'appuie sur les dossiers, les liens entre notes, les tags et les métadonnées. Plusieurs racines peuvent être déclarées pour consulter différentes collections. Les fonctions qui créent des objets et les accès des agents utilisent la racine principale selon leurs droits.

Les index de recherche sont conservés séparément dans le profil utilisateur. Ils servent à retrouver les documents et peuvent être reconstruits à partir des notes. Certaines données de travail, comme les dossiers Constat ou la file de validation, résident également dans le profil : sauvegarder uniquement les fichiers Markdown ne suffit donc pas à sauvegarder tout l'environnement.

## Les fonctions du cœur

### Écrire, organiser et naviguer

L'interface réunit l'explorateur de fichiers, l'édition Markdown, la recherche dans la note, les liens entrants, les tags et le graphe de relations. Les instantanés et la corbeille accompagnent les opérations sur les notes.

Le graphe rend les relations explicites visibles. Il permet d'explorer ce qui relie les documents ; la présence d'un lien ne constitue pas, à elle seule, une preuve de corroboration.

### Retrouver les bons passages

PRISME propose plusieurs approches complémentaires :

| Recherche | Ce qu'elle apporte |
|---|---|
| **Plein texte** | Retrouver des termes dans les notes et leurs passages grâce à un index SQLite FTS5 |
| **Sémantique** | Rechercher des textes proches par le sens avec un fournisseur d'embeddings configuré |
| **Hybride** | Combiner les classements lexicaux et sémantiques |
| **En arbre** | Partir de résultats pertinents, explorer leurs liens et sélectionner un contexte avant une réponse IA |

La recherche sémantique nécessite un modèle et la vectorisation du corpus. Le fournisseur peut être une API, Ollama ou le plugin **Embeddings locaux**. La recherche en arbre peut construire son contexte sans appeler de modèle ; la génération d'une réponse est une opération distincte.

### Importer des sources avec ENGRAM

ENGRAM prend en charge des exports de conversations ChatGPT, Claude et Mistral, ainsi que des entrées texte et HTML. L'import passe par une inspection du contenu et produit des notes structurées avec des références à la source et à ses passages.

L'identification des contenus permet de reconnaître les réimports et de limiter les doublons. Les formats pris en charge ont chacun leur extracteur : ENGRAM ne doit pas être considéré comme un convertisseur universel de documents.

### Conserver la provenance

Les métadonnées `prisme_*` permettent de conserver des identifiants, des références et des informations sur la production et l'enregistrement des notes. Une fiche de provenance permet de les consulter et de les compléter.

Cette traçabilité aide à distinguer les sources importées, les productions des outils et les validations. Elle documente l'origine d'un contenu ; elle ne garantit pas automatiquement sa véracité.

### Structurer les connaissances et les actions

Les fiches d'objets sont enregistrées dans le vault en Markdown.

| Objet | Usage |
|---|---|
| **Source** | Conserver une référence et la relier aux notes qui l'utilisent |
| **Décision** | Expliciter un choix et sa justification |
| **Hypothèse** | Formuler un énoncé et un critère de réfutation |
| **Prédiction** | Annoncer une probabilité, une échéance et une condition de résolution, puis conserver le résultat observé |
| **Entité** | Décrire une personne, une organisation, un lieu, un produit ou un autre objet d'étude |
| **Tâche** | Définir une action, son critère de fin et son état d'avancement |

Une file de validation permet de relire, compléter, accepter ou rejeter les propositions. Les règles d'entrée directe des imports se configurent séparément. Les agents ont des droits explicites ; l'écriture directe ne leur est pas accordée par défaut.

Le contrat des objets est détaillé dans [la documentation dédiée](docs/OBJETS.md).

## Les neuf plugins

Les plugins complètent le cœur et disposent chacun d'un guide pratique dans le dossier **[`guides-plugins/`](guides-plugins/README.md)**.

| Plugin | Fonction | Guide |
|---|---|---|
| **ArXiv** | Rechercher des publications scientifiques depuis une note, puis synthétiser leurs résumés | [Utiliser ArXiv](guides-plugins/arxiv.md) |
| **DuckDuckGo / DDG** | Effectuer une recherche web contextualisée et produire une synthèse des résultats | [Utiliser DDG](guides-plugins/duckduckgo.md) |
| **Context Builder** | Constituer un corpus de notes par sélection ou exploration de liens, puis l'interroger | [Assembler un contexte](guides-plugins/context.md) |
| **Prompts Manager** | Créer et réutiliser des consignes de réponse ; sélection automatique dans DDG et RSS | [Gérer les prompts](guides-plugins/prompts.md) |
| **RSS** | Gérer des flux, sélectionner des articles et préparer des synthèses de veille | [Organiser une veille](guides-plugins/rss.md) |
| **OSINT Cross-Reference** | Examiner et recouper des indices publics à partir de plusieurs types d'identifiants | [Utiliser OSINT](guides-plugins/osint-cx.md) |
| **Embeddings locaux** | Exécuter un modèle ONNX sur la machine pour la recherche sémantique | [Configurer les embeddings](guides-plugins/embeddings-locaux.md) |
| **Constat** | Constituer des dossiers d'analyse, coter les sources et confronter des hypothèses | [Utiliser Constat](guides-plugins/constat.md) |
| **Calibration** | Conserver les paris de référence et calculer les scores après résolution | [Évaluer ses prédictions](guides-plugins/calibration.md) |

Le gestionnaire **Plugins** permet de consulter leur état, de les activer ou de les désactiver et de renseigner les secrets requis. Certains plugins ont des dépendances ou des services propres : leur guide précise les conditions nécessaires.

## De l'analyse à la prédiction

### Constat : construire et relire une analyse

**Constat est intégré directement à PRISME. Aucune extension Firefox n'est nécessaire.**

Un dossier commence par une question, un périmètre, un horizon d'étude et une décision à éclairer. Vous y ajoutez des copies de notes, du texte ou des fichiers HTML enregistrés, puis cotez les sources et établissez un relevé déterministe.

Les étapes d'analyse assistées par IA sont lancées explicitement, avec un aperçu des messages transmis au modèle. Les sorties peuvent être relues, corrigées et validées. Les révisions et les dépendances entre étapes restent identifiables dans le dossier.

L'**ACH**, ou analyse des hypothèses concurrentes, confronte plusieurs hypothèses aux éléments disponibles. Son classement exprime leur compatibilité avec le corpus ; il ne fournit pas automatiquement une probabilité.

Le bouton **Créer un dossier de démonstration** permet de découvrir le parcours avec des documents fictifs, sans appel IA.

### Calibration : mesurer des paris formulés à l'avance

Le parcours disponible est le suivant :

1. Dans Constat, valider une ACH puis choisir une hypothèse à **verser comme prédiction dans PRISME**.
2. Renseigner l'événement, sa probabilité entre 0 et 1, son échéance et son critère de résolution.
3. Dans Constat, ouvrir **Prédictions et Calibration**, relire et accepter la proposition.
4. Relire ses pièces puis **confirmer la copie dans Calibration avant le jour de l'échéance et avant de connaître son résultat**, depuis ce panneau ou depuis Calibration.
5. Après observation, résoudre la prédiction avec une date, un résultat et une preuve.
6. Actualiser Calibration pour consulter les scores et les éventuelles exclusions.

Le plugin calcule notamment le **score de Brier**, la **log loss** et des statistiques de calibration par domaine et par horizon. Il fonctionne sans modèle IA et sans service distant.

Pour un pari à `0,8` dont le résultat est « oui », le Brier vaut `0,04` et la log loss environ `0,2231`. Le [guide Calibration](guides-plugins/calibration.md) propose un essai fictif complet et explique les exclusions.

**Les responsabilités restent séparées :** Constat prépare l'analyse, le cœur conserve la fiche Prédiction, Calibration calcule les mesures. Le plugin active aussi les champs de validité de l'**horloge du monde**, distincts de l'échéance du pari.

Constat conserve les passages exacts des sources, les corrections motivées, les validations et les contradictions déclarées. Ces pièces accompagnent désormais le pari dans Calibration. L'acceptation de la prédiction et sa copie restent deux actions distinctes et explicites.

## Installation depuis les sources

### Prérequis

- **Python 3.12 ou supérieur**, avec `pip` ;
- **Git** pour cloner le dépôt ;
- un navigateur web ;
- un service IA configuré uniquement pour les fonctions qui en ont besoin.

Windows est la plateforme visée pour la distribution à venir. Les autres systèmes ne sont pas présentés comme des distributions validées.

### Installation sous Windows — PowerShell

Depuis le dossier dans lequel vous souhaitez installer le projet :

```powershell
git clone https://github.com/Othman-Benbrahim/PRISME.git
Set-Location .\PRISME
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe prisme.py
```

La commande `py -3.12` utilise Python 3.12. Si une autre version compatible est installée, adaptez ce sélecteur. L'appel direct au Python de `.venv` évite d'avoir à activer l'environnement PowerShell.

Le navigateur s'ouvre sur **http://localhost:5000**. L'application s'exécute sur votre machine, avec une interface dans le navigateur. Gardez le terminal ouvert pendant l'utilisation ; **Ctrl+C** arrête le serveur local.

Pour les lancements suivants, depuis le dossier du projet :

```powershell
.\.venv\Scripts\python.exe prisme.py
```

### Premier démarrage

1. Choisissez le dossier de notes à utiliser comme vault. Un petit dossier d'essai permet de découvrir les fonctions avant de travailler sur votre corpus principal.
2. Configurez l'URL du fournisseur IA, le modèle et sa clé si nécessaire, puis testez la connexion pour les fonctions assistées.
3. Ouvrez une note et vérifiez la recherche, les liens et les tags.
4. Consultez **Plugins**, puis ouvrez le guide correspondant à l'outil souhaité.
5. Pour la recherche sémantique, configurez un fournisseur, activez-la et lancez la vectorisation du vault.

PRISME prend en charge des services compatibles avec le format OpenAI ainsi que le dialecte Anthropic. Un serveur local compatible, tel qu'Ollama ou LM Studio, peut servir de fournisseur conversationnel. Le choix des modèles disponibles dépend du service utilisé.

Les modèles conversationnels et les modèles d'embeddings ont des réglages distincts. Installer un modèle ONNX ne configure pas automatiquement l'assistant conversationnel.

### Dépendances optionnelles

Les embeddings locaux nécessitent leurs dépendances propres :

```powershell
.\.venv\Scripts\python.exe -m pip install -r plugins/embeddings-locaux/requirements.txt
```

Le modèle doit ensuite être téléchargé ou sélectionné dans le panneau **Embeddings**.

Pour utiliser la bibliothèque de recherche prévue par le plugin DDG :

```powershell
.\.venv\Scripts\python.exe -m pip install ddgs
```

Consultez les guides pour les connecteurs OSINT et leurs outils facultatifs. Arrêtez et relancez PRISME après l'installation de dépendances. **Node.js n'est pas nécessaire pour utiliser Constat** : il sert aux tests de son interface.

## Données, confidentialité et sauvegarde

PRISME conserve le vault et son profil sur la machine. **Cela ne signifie pas que toutes ses fonctions sont hors ligne.**

| Élément | Emplacement ou comportement |
|---|---|
| Notes, fiches d'objets et rapports enregistrés | Dans le vault |
| Configuration, index et données de travail des plugins | Dans le profil utilisateur, normalement `%USERPROFILE%\.prisme` sous Windows |
| Dossiers Constat | Dans le profil, avec des exports JSON pour les sauvegarder ou les transférer |
| Copies de référence de Calibration | Dans `Objets/Calibration/`, à l'intérieur du vault |
| Appels à un modèle distant | Les contenus nécessaires à l'opération sont envoyés au fournisseur configuré |
| Recherche web, RSS, arXiv et connecteurs OSINT | Communications avec les sources et services sollicités |
| Embeddings ONNX locaux | Calcul sur la machine après récupération du modèle |

L'interface actuelle charge aussi certaines bibliothèques et polices depuis des services en ligne. Un fonctionnement intégralement hors ligne de l'ensemble de l'interface n'est donc pas garanti.

Sous Windows, les clés gérées par PRISME bénéficient du chiffrement DPAPI. Les notes, les dossiers d'analyse et leurs exports ne sont pas chiffrés par ce mécanisme. Le même chiffrement des secrets n'est pas disponible sur les autres systèmes.

Pour conserver votre environnement, sauvegardez **le vault et le profil utile**, et exportez les dossiers Constat importants. La variable `PRISME_DATA_DIR` permet de choisir un autre emplacement de profil, notamment pour isoler des essais.

## Agents et MCP

PRISME expose une API HTTP locale sous **`/api/v1/`**. Les agents disposent de clés avec des droits de lecture, de proposition et, uniquement si cela est accordé, d'écriture. Les accès sont journalisés et bornés au périmètre autorisé.

Un adaptateur **MCP** traduit les appels d'un client vers cette API. Il permet de proposer des intégrations avec des outils tels que Claude Code tout en conservant les contrôles d'accès et la file de validation de PRISME.

L'adaptateur est fourni dans [`mcp/prisme_mcp.py`](mcp/prisme_mcp.py). Son protocole fait l'objet de tests automatisés ; la validation de bout en bout avec un client réel reste à compléter. Voir [la documentation MCP](docs/branches/e10-mcp.md) pour son fonctionnement et sa configuration.

## Développement et vérification

Le code distingue le cœur, les plugins et l'interface. Les choix structurants sont documentés dans des fiches de décision.

| Dossier ou fichier | Rôle |
|---|---|
| `prisme.py` | Lanceur de l'application |
| `prisme_core/` | Gestion des notes, recherche, provenance, objets, API et interface |
| `plugins/` | Modules spécialisés et leurs ressources |
| `guides-plugins/` | Guides destinés aux utilisateurs |
| `mcp/` | Adaptateur pour les clients MCP |
| `tests/` | Tests Python |
| `evaluation/` | Cas de référence pour évaluer la recherche |
| `docs/` | Architecture, décisions et suivi des étapes |

Depuis la racine du dépôt, avec les dépendances nécessaires installées :

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONHASHSEED = "0"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Pour les tests d'interface de Constat, avec Node.js et npm :

```powershell
npm ci --prefix plugins/constat --ignore-scripts --no-audit --no-fund
npm test --prefix plugins/constat
```

Les contrôles automatisés complètent les vérifications visuelles et les essais sur un corpus réel. La pertinence de la recherche dépend du corpus, des réglages et des modèles ; les cas de référence sont décrits dans [`evaluation/`](evaluation/README.md).

Pour signaler un problème, indiquez les étapes permettant de le reproduire, le système, la version de Python et le plugin concerné. Les contributions passent par des pull requests au périmètre explicite. Le document [PLUGIN-DEVELOPMENT.md](PLUGIN-DEVELOPMENT.md) décrit l'API des plugins.

# PRISME — état et prochaines étapes

Arrêté au commit `8ecb7a2` (PR #23, « Constat : preuves traçables et transfert vers
Calibration ; nettoyage OSINT »), le 2026-09-19.

---

## 1. Où en est le projet

**Toutes les étapes numérotées sont fusionnées.**

| Étape | Objet | État |
|---|---|---|
| Base → E8 → E1 → E2 → E3 → E4 → E5 → E6 → E7 | Fondations : découpage, API plugins, index SQLite, provenance, ENGRAM, objets Source, API agents, embeddings | Fait |
| E12 | Plusieurs racines de vault | Fait |
| E13 | Recherche en arbre | Fait |
| E10 | Adaptateur MCP au-dessus de `/api/v1/` | Fait |
| **E11** | Types d'objets — **sans** calcul de calibration | Fait |
| **plugin-calibration** | Brier, log loss | Fait |
| **plugin-constat-integre** | Dossiers et ACH **dans PRISME**, sans extension Firefox | Fait |
| **E9** | Distribution Windows | Fusionnée, pour construire l'exécutable |

**Vérifications au dernier commit** : 436 tests Python, 141 tests JavaScript, et un
parcours Chromium complet jusqu'aux scores fictifs — Brier 0,0400, log loss 0,2231.

### Publication

| Version | État |
|---|---|
| `v0.1.0-rc.1` — commit `d0e2232` | Publiée le 19/09 à 17:53, avec l'application portable Windows x64 |
| `v0.1.0-rc.2` — commit `8ecb7a2` | À publier : archive des sources prête, notes rédigées |

---

## 2. Ce qui est en cours

**`docs-guides-plugins`** — les guides des plugins, qui précèdent E9. C'est le seul
chantier ouvert.

---

## 3. Prochaines étapes

### Immédiat

1. **Publier `v0.1.0-rc.2`** — et y joindre l'exécutable portable reconstruit sur
   `8ecb7a2`. Sans lui, la release annonce une application portable qu'elle ne livre pas.
2. **Terminer `docs-guides-plugins`** — dernier préalable à E9.
3. **Reconstruire l'exécutable** sur le commit courant : rc.1 a été bâtie sur `d0e2232`,
   donc son binaire ignore Constat, Calibration et le nettoyage OSINT.

### Dettes à solder avant une version stable

| Sujet | Pourquoi maintenant |
|---|---|
| **Découpage de `core.css`** | 293 caractères de marge sur un plafond de 20 000. La prochaine étape qui touche ce fichier fait sauter le garde-fou d'E8. |
| **Synchronisation des rejets** | Décidée en **0024**, jamais appliquée. Environ une demi-journée. |
| **Chiffrement hors Windows** | DPAPI est propre à Windows. Si la distribution vise macOS ou Linux, les clés y restent en clair — signalé au démarrage, mais en clair. |
| **Gel des objets** | Prévu par **0017**, non implémenté. |
| **Usage réel soutenu** | Jamais fait. C'est le seul essai capable d'invalider ce que les tests confirment entre eux. |

### À vérifier une fois, puis oublier

- **L'adaptateur MCP sur un vrai Claude Code.** Les tests reproduisent le protocole
  fidèlement, mais aucun client réel ne s'y est branché.
- **Le chargement d'`onnxruntime` depuis l'exécutable gelé** — le point que la décision
  **0030** désignait comme seul capable de l'invalider, et qui ne se voit qu'au build.

---

## 4. Trois écarts à corriger dans la documentation

Ce sont des divergences entre ce qui est écrit et ce qui existe. Aucune n'est grave ;
toutes vieillissent mal si on les laisse.

**La décision 0031 est dépassée.** Elle actait que Constat resterait une extension
Firefox versant ses hypothèses par `/api/v1/`, avec PRISME comme seul dépositaire des
scores. L'implémentation a pris l'autre voie : `plugin-constat-integre` place les
dossiers et l'ACH **dans** PRISME, sans extension. Le résultat est défendable — un seul
outil, un seul historique, pas de pont à maintenir — mais la fiche dit encore le
contraire. Elle mérite un statut « remplacée », avec une ligne sur ce qui a fait changer
d'avis. Conséquence à noter : l'API des agents n'a toujours **aucun client extérieur**,
ce qui était l'autre intérêt de ce montage.

**La feuille de route annonce encore 359 tests** dans sa dernière ligne. Le chiffre réel
est 436 Python et 141 JavaScript. C'est mon chiffre d'E10 qui a survécu à quatre étapes.

**L'ordre affiché reste E12 → E13 → E10 → E11 → E9**, alors que E9 est fusionnée et que
deux plugins se sont intercalés. Le tableau gagnerait à refléter l'ordre réellement suivi.

---

## 5. Ce qui n'a pas changé et ne doit pas changer

Rappel des invariants, parce qu'ils survivent aux étapes :

- **`vault.py`** est la garde. Elle sert l'interface, les plugins et `/api/v1/` à la
  fois. Toute modification doit échouer du côté restreint, jamais du côté permissif.
- **L'IA propose, l'auteur valide.** Une proposition d'agent passe par la file, même
  parfaitement vérifiable.
- **Tout ce qu'une machine écrit est estampillé.**
- **Aucun fichier monolithique** : 20 000 caractères, mesurés sur le texte et non sur
  les octets du disque.
- **Mesurer, pas supposer.** Précédent : l'arbre d'E13 ne fait pas économiser de jetons
  — c'est le plafond de budget qui économise ; l'arbre apporte du rappel par les liens.
- **La machine de l'auteur est Windows.** Encodage, fins de ligne, verrous de fichiers,
  environnement des sous-processus : des tests verts ailleurs ne prouvent rien.

## Documentation

- [Guides des neuf plugins](guides-plugins/README.md)
- [Objets typés et validation](docs/OBJETS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Décisions de conception](docs/decisions/README.md)
- [Développer un plugin](PLUGIN-DEVELOPMENT.md)
- [Évaluation de la recherche](evaluation/README.md)
- [Évolutions depuis Second Brain V1](docs/RUPTURES.md)
- [Feuille de route](docs/FEUILLE-DE-ROUTE.md)

## Origine et licences

PRISME est développé par **Othman Ben Brahim**. Il est issu d'une refonte de Second Brain V1, dont la base historique est conservée sous l'étiquette Git `base-v1`.

## Badges GitHub

![Tests](https://github.com/Othman-Benbrahim/PRISME/actions/workflows/ci.yml/badge.svg)
![Version](https://img.shields.io/github/v/release/Othman-Benbrahim/PRISME)
![License](https://img.shields.io/github/license/Othman-Benbrahim/PRISME)
![Python](https://img.shields.io/badge/python-3.12+-blue)

Le fichier [`LICENSE`](LICENSE) à la racine indique la **licence MIT**. Le plugin Constat reprend des composants du [projet Constat](https://github.com/Othman-Benbrahim/constat) et conserve sa **licence AGPL-3.0**, disponible dans [`plugins/constat/LICENSE`](plugins/constat/LICENSE). Les dépendances et les modèles conservent leurs licences respectives.

[Deepwiki](https://deepwiki.com/Othman-Benbrahim/PRISME)
