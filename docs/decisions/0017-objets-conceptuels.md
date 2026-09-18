# 0017 · Objets conceptuels

- **Statut** : appliquée en E5 pour le type Source ; amendée par 0021 (entrée directe des imports en masse) et par la révision ci-dessous ; les autres types restent reportés
- **Écrite** : 2026-09-16

**Retenu.** L'IA propose, l'auteur valide. File d'attente hors du vault, avec passage
source, actions accepter / corriger / fusionner / rejeter, rejets mémorisés, traitement
par lot. Premier type : **Source** (statuts « citée » et « ingérée », dédoublonnage par URL
normalisée, DOI ou empreinte).

**Reporté.** Décision, hypothèse, prédiction, entité OSINT, tâche. Le mécanisme de gel est
prévu dans le modèle mais pas implémenté.

## Révision du 17 septembre 2026

- **Tout ne passe plus par la file** : voir [0021](0021-entree-directe-des-imports-en-masse.md).
- **Une décision garde sa raison** (inspiré d'Utopia, fiche 0026) : accepter, corriger, fusionner ou rejeter propose un champ « raison » facultatif. La raison est conservée avec la décision et relue par l'IA avant toute nouvelle proposition, pour qu'un choix ponctuel ne soit pas pris pour une règle générale.
- **Les fusions sont réversibles** (inspiré d'Utopia, fiche 0027) : un journal des fusions permet de les annuler.

## Application en E5

Le type **Source** existe : une note du vault dans `Objets/Sources/`, clé normalisée
dans l'en-tête, statuts « citée » et « ingérée », dédoublonnage par URL normalisée, DOI,
identifiant arXiv ou ISBN. La file de validation vit hors du vault
(`~/.prisme/objets/file.json`), avec accepter / corriger / fusionner / rejeter, raison
facultative conservée, rejets mémorisés et relus avant toute nouvelle proposition, et
journal des fusions réversible (`prisme_fusions` + alias).

Reportés comme prévu : décision, hypothèse, prédiction, entité OSINT, tâche, et le
mécanisme de gel.
