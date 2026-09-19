# Décisions d'architecture

Une fiche par décision. Une décision ne se modifie pas en silence : on ajoute une révision datée dans la fiche, ou une nouvelle fiche qui la remplace.

Sources d'inspiration examinées : la roadmap *Lux Kybernetica* (projet tiers), `alphaXiv/OpenResearch`, le RAG de *Studio Littéraire 0.9.1* et `deeplethe/utopia`. Aucune n'est reproduite ; seules des idées sont reprises, et chaque fiche dit lesquelles.

Chaque fiche indique : le **statut** (acceptée, appliquée, remplacée), la **date**, ce qui a été **retenu** et pourquoi, et ce qui a été **écarté**.

| N° | Décision | Statut |
|---|---|---|
| 0001 | [Nouveau projet, base V1 figée](0001-nouveau-projet-base-v1-figee.md) | appliquée (étape 00) |
| 0002 | [Nom et préfixes](0002-nom-et-prefixes.md) | appliquée en E8 (nom, profil, en-tête) et E1 (API) |
| 0003 | [Compatibilité Obsidian](0003-compatibilite-obsidian.md) | acceptée ; partiellement appliquée en E1 (données internes hors du vault) |
| 0004 | [Développement puis publication](0004-developpement-puis-publication.md) | acceptée, non encore appliquée |
| 0005 | [Aucun fichier monolithique](0005-aucun-fichier-monolithique.md) | appliquée en E8 |
| 0006 | [API des plugins : rupture nette](0006-api-des-plugins-rupture-nette.md) | appliquée en E1 |
| 0007 | [Gestionnaire de plugins](0007-gestionnaire-de-plugins.md) | appliquée en E1 |
| 0008 | [Source des plugins](0008-source-des-plugins.md) | appliquée en E1 |
| 0009 | [Hooks synchrones](0009-hooks-synchrones.md) | appliquée en E1 |
| 0010 | [Index SQLite dans le profil](0010-index-sqlite-dans-le-profil.md) | appliquée en E2 |
| 0011 | [Double granularité](0011-double-granularite.md) | appliquée en E2 |
| 0012 | [Identifiants posés au besoin](0012-identifiants-poses-au-besoin.md) | appliquée en E3 |
| 0013 | [ENGRAM : toutes les sources, un seul contrat](0013-engram-toutes-les-sources-un-seul-contrat.md) | appliquée en E4 |
| 0014 | [Forme des notes importées](0014-forme-des-notes-importees.md) | appliquée en E4 |
| 0015 | [Fichiers d'origine](0015-fichiers-d-origine.md) | appliquée en E4 |
| 0016 | [Passages retirés d'une source](0016-passages-retires-d-une-source.md) | appliquée en E4 |
| 0017 | [Objets conceptuels](0017-objets-conceptuels.md) | appliquée en E5 pour le type Source ; autres types en E11 |
| 0018 | [Accès des agents](0018-acces-des-agents.md) | appliquée en E6 ; adaptateur MCP en E10 |
| 0019 | [Recherche sémantique](0019-recherche-semantique.md) | appliquée en E7 ; plugin ONNX à écrire |
| 0020 | [Méthode de travail](0020-methode-de-travail.md) | appliquée depuis l'étape 00 |
| 0021 | [Entrée directe des imports en masse](0021-entree-directe-des-imports-en-masse.md) | appliquée en E5, pour le type Source |
| 0022 | [Horloges des objets](0022-horloges-des-objets.md) | appliquée en E3 (horloge d'enregistrement) ; horloge du monde précisée par 0026 |
| 0023 | [Clés et secrets chiffrés (DPAPI)](0023-cles-et-secrets-chiffres-dpapi.md) | appliquée en E1 |
| 0024 | [Synchronisation entre machines](0024-synchronisation-entre-machines.md) | acceptée, non encore appliquée |
| 0025 | [Calibration en plugin](0025-calibration-en-plugin.md) | acceptée, non encore appliquée |
| 0026 | [Activation de l'horloge du monde](0026-horloge-du-monde-activee.md) | acceptée, non encore appliquée |
| 0027 | [Découpage et ordre des étapes restantes](0027-ordre-des-etapes-restantes.md) | acceptée |
| 0028 | [Plusieurs racines de vault](0028-plusieurs-racines-de-vault.md) | appliquée en E12 |
| 0029 | [Recherche en arbre](0029-recherche-en-arbre.md) | acceptée, à appliquer (E13) |
