# Décisions d'architecture

Décisions prises le 16 septembre 2026, avant tout développement, après examen de
trois sources d'inspiration : la roadmap *Lux Kybernetica* (projet tiers, pris comme
inspiration et non comme structure à reproduire), le dépôt `alphaXiv/OpenResearch`
et le RAG de *Studio Littéraire 0.9.1*.

Chaque décision indique ce qui a été retenu, pourquoi, et les options écartées.
Une décision ne se modifie pas en silence : on ajoute une entrée qui la remplace.

---

## D01 — Nouveau projet, base V1 figée

**Retenu.** PRISME est un nouveau dépôt. Son premier commit reprend Second Brain V1
à l'identique (étiquette `base-v1`). Le dépôt `Second-Brain` n'est plus modifié.

**Pourquoi.** La V1 est considérée comme obsolète ; elle sert de support, pas de cible
de compatibilité.

**Écarté.** Une branche `v2` dans le dépôt `Second-Brain`.

## D02 — Nom et préfixes

**Retenu.** Dépôt `PRISME`, package `prisme_core`, API des plugins `prisme_core.api`,
profil `~/.prisme/`, champs de frontmatter préfixés `prisme_`, exécutable `PRISME.exe`,
en-tête des clés d'agents `X-Prisme-Key`.

**Pourquoi.** Un paquet `prisme` existe déjà sur PyPI : `prisme_core` évite tout conflit
d'import. Le préfixe `prisme_` reste lisible dans Obsidian sans connaître le projet.

**Écarté.** Préfixe court `pm_` (opaque) ; bloc YAML imbriqué `prisme:` (mal affiché
par le panneau Propriétés d'Obsidian).

## D03 — Compatibilité Obsidian

**Retenu.** Le vault reste ouvrable par Obsidian : YAML standard, wikilinks et `#tags`
inchangés, données internes dans des dossiers cachés. PRISME est l'outil prioritaire.

**Limite assumée.** Le gel des objets et la provenance ne sont garantis que dans PRISME ;
Obsidian peut modifier ces champs.

## D04 — Développement puis publication

**Retenu.** PRISME est développé d'abord pour son auteur, puis publié pour le grand public.
Un import de vault V1 et un guide des ruptures sont prévus avant publication (E9).

## D05 — Aucun fichier monolithique

**Retenu.** Le cœur Python est un package de modules courts ; l'interface est découpée
en fichiers CSS et JS par zone ; chaque plugin est chargé comme fichier distinct.

**Pourquoi.** Ne pas tout mettre dans le même panier : une erreur dans un fichier ne doit
faire tomber que sa propre fonctionnalité.

## D06 — API des plugins : rupture nette

**Retenu.** Seule `prisme_core.api` existe à partir de E1. Les six plugins hérités sont
migrés en même temps. Une passerelle temporaire (`second_brain`) existe pendant E8 et
disparaît en E1.

**Écarté.** Une passerelle de compatibilité permanente.

## D07 — Gestionnaire de plugins

**Retenu.** Installer, activer, désactiver, désinstaller depuis l'interface, comme les
extensions d'un navigateur. Le cœur fonctionne sans aucun plugin ; poser un dossier à la
main dans `plugins/` reste possible.

**Détails.** Chaque plugin a son préfixe de routes (`/api/plugins/<id>/`). Désactiver
bloque ses routes et son interface sans redémarrage ; désinstaller envoie son dossier à la
corbeille ; une mise à jour demande un redémarrage. Le manifest déclare `api_version` et
les permissions ; ces permissions **informent** l'utilisateur mais ne confinent pas le
code (Python ne sait pas isoler un plugin).

## D08 — Source des plugins

**Retenu.** ZIP local ou URL HTTPS.

**Garde-fous.** HTTPS uniquement, taille maximale, refus des chemins `../` et absolus dans
l'archive, écran de confirmation (source, manifest, permissions), empreinte SHA-256
mémorisée, URL d'origine conservée.

**Écarté.** Catalogue centralisé (responsabilité éditoriale).

## D09 — Hooks synchrones

**Retenu.** Les plugins abonnés à un événement s'exécutent avant la confirmation, avec un
délai maximal par hook au-delà duquel le plugin est abandonné et signalé. Les traitements
lourds du cœur (indexation, ingestion) tournent en tâche de fond, hors hooks.

**Risque accepté.** Un plugin lent ralentit la sauvegarde.

## D10 — Index SQLite dans le profil

**Retenu.** `~/.prisme/index/<empreinte du chemin du vault>.db`, avec un fichier de
correspondance empreinte → chemin.

**Pourquoi.** Aucun risque de corruption par un service de synchronisation ; l'index se
reconstruit toujours depuis les `.md`.

**Écarté.** Base dans le vault.

## D11 — Double granularité

**Retenu.** Une table par fichier (tags, liens, graphe) et une table par segment (recherche).

**Découpage.** Un segment par titre de niveau 1 à 3 ; notes sans titres : paragraphes
regroupés vers 1 500 caractères ; sections longues redécoupées au-delà d'environ 4 000
caractères, sur une fin de paragraphe. Blocs de code jamais coupés. Chaque segment porte
sa note, son titre, sa position et une empreinte de contenu.

## D12 — Identifiants posés au besoin

**Retenu.** Une note humaine ne reçoit `prisme_id` que lorsque quelque chose y fait
référence. Les notes produites par une machine en ont un dès leur création. Identifiant
stable (UUID court) plutôt que chemin.

**Détails.** La pose se limite au frontmatter, après un instantané. Une référence encore
fondée sur un chemin devient « orpheline » si la note est renommée hors de PRISME ; le
rattachement par contenu identique est proposé, jamais deviné.

## D13 — ENGRAM : toutes les sources, un seul contrat

**Retenu.** Exports ChatGPT et Claude, Markdown, texte, HTML, dépôts, PDF, DOCX, EPUB,
images. Un contrat d'extraction commun (inspiré de Studio Littéraire) : vérification du
fichier, SHA-256 avant et après extraction, enregistrement du moteur, de sa version et de
sa configuration.

**Répartition.** Formats légers : plugins en Python pur. Formats lourds : plugin qui pilote
un outil externe dans son propre environnement.

## D14 — Forme des notes importées

**Retenu.** Une note par source ; au-delà d'un seuil réglable (200 000 caractères au
départ), répartition en parties reliées par une note sommaire. Coupure entre deux échanges
ou chapitres. Les identifiants de passage sont rattachés à la source, pas à la partie.

## D15 — Fichiers d'origine

**Retenu.** Copie dans `_sources/` ou simple référence, au choix pour chaque source, avec
une valeur par défaut réglable. La provenance garde toujours l'empreinte, le chemin
d'origine et le mode. Une commande de contrôle signale les sources disparues ou modifiées.

## D16 — Passages retirés d'une source

**Retenu.** Conservés en fin de note sous « Passages retirés de la source », dans un
callout `> [!danger]` (rouge dans Obsidian et PRISME), avec date, identifiant et empreinte
de la version responsable. Le signal se propage aux notes qui les citent. Un passage qui
réapparaît quitte l'archive.

**Identité des passages.** Algorithme repris de Studio Littéraire : correspondance exacte,
puis texte identique déplacé et unique, puis texte retouché à 65 % au moins avec une avance
nette ; dans le doute, nouvel identifiant.

## D17 — Objets conceptuels

**Retenu.** L'IA propose, l'auteur valide. File d'attente hors du vault, avec passage
source, actions accepter / corriger / fusionner / rejeter, rejets mémorisés, traitement
par lot. Premier type : **Source** (statuts « citée » et « ingérée », dédoublonnage par URL
normalisée, DOI ou empreinte).

**Reporté.** Décision, hypothèse, prédiction, entité OSINT, tâche. Le mécanisme de gel est
prévu dans le modèle mais pas implémenté.

## D18 — Accès des agents

**Retenu.** API HTTP locale (`127.0.0.1`) avec une clé par agent : affichée une seule fois,
seule son empreinte est stockée, révocable, journalisée. Droits par défaut : lecture et
proposition dans la file. Écriture directe seulement sur accord explicite, clé par clé.
Plafond de propositions en attente par clé.

**Reporté.** Adaptateur MCP au-dessus de la même API.

**Écarté.** CLI dédiée.

## D19 — Recherche sémantique

**Retenu.** Interface « fournisseur d'embeddings » dans le cœur, avec trois voies :
plugin local ONNX Runtime + modèle e5 (exception assumée à la règle de dépendances :
bibliothèque compilée dans le plugin, modèle téléchargé à part) ; API compatible OpenAI
(`/embeddings`) avec paramétrage séparé du chat ; Ollama.

**Règles.** Pas de mélange de modèles dans un index (changement = revectorisation annoncée) ;
mode distant désactivé par défaut, avec avertissement ; mode actif toujours visible ;
fusion FTS5 + vecteurs par RRF (k = 60) puis diversification ; repli sur FTS5 seul en cas
d'absence ou de panne ; vecteurs réutilisés par empreinte de segment.

## D20 — Méthode de travail

**Retenu.** Fichiers préparés localement, poussés avec PowerShell et GitHub CLI. Une branche
documentée par étape, une pull request par étape validée. Tests en `unittest` (bibliothèque
standard) avant chaque pull request, et questions de référence pour la recherche.
