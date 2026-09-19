# 0025 · Calibration en plugin

- **Statut** : implémentée après E11, en revue dans `plugin-calibration`
- **Écrite** : 2026-09-19

## Décision

Mesurer la qualité des prédictions — score de Brier, log loss, courbes de calibration,
détection de biais systématiques — se fait dans un **plugin dédié**, pas dans le cœur.

Avec un partage net :

- **Le cœur fournit le type Prédiction** : ses champs, sa validation, son entrée dans le
  vault comme objet (0017). Un plugin ne peut pas scorer des prédictions qui n'existent
  pas, et le format doit rester stable même sans le plugin.
- **Le plugin fait le calcul** : scoring, agrégation, rapports.

Même partage qu'ailleurs dans PRISME : le cœur tient le format, le plugin fait le calcul.

## Pourquoi pas dans le cœur

- La calibration n'intéresse pas tout le monde ; le cœur doit rester utile sans elle.
- Le calcul demandera vraisemblablement des dépendances que le cœur s'interdit (0005).
- Une méthode de scoring évolue ; un format de note, non. Les séparer évite que la
  seconde suive les soubresauts de la première.

## Conséquence

Le type Prédiction est un prérequis (E11). Le plugin vient après, et sa disparition ne
doit rien casser : une prédiction non scorée reste une note valide.
