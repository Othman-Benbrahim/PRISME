# 0031 · Constat verse des hypothèses, PRISME score les prédictions

- **Statut** : acceptée, à appliquer (après E11)
- **Écrite** : 2026-09-19

## Problème

L'auteur maintient une extension Firefox, **Constat**, qui construit des dossiers
d'investigation : corpus versé depuis la navigation, comptages de corroboration, silences
mesurés, classements ACH. L'idée envisagée était de l'adapter pour qu'elle fasse office de
calibration, à la place du plugin prévu par [0025](0025-calibration-en-plugin.md).

Examen du dépôt : Constat n'enregistre **ni probabilité, ni date butoir, ni condition de
résolution**. Aucun Brier, aucun log loss. Ce n'est pas une lacune mais un parti pris,
écrit dans son README :

> « Aucun nombre produit par le modèle n'entre dans un relevé. »

Lui ajouter ces trois champs reviendrait à lui faire faire un autre métier que le sien, et
à abîmer le principe qui fait sa valeur.

## Décision

Les deux outils gardent leur métier, et se joignent **au niveau de l'hypothèse**.

- **Constat reste la source des hypothèses.** Son classement ACH — des hypothèses
  concurrentes adossées à un corpus — est exactement l'entrée d'une prédiction. Il ne
  manque que la probabilité, l'horizon et le critère de résolution.
- **Un bouton « verser comme prédiction dans PRISME »**, qui POSTe sur `/api/v1/` avec une
  clé d'agent. C'est l'API d'E6, et ce serait son premier client extérieur — donc sa
  première épreuve réelle.
- **L'auteur complète les trois champs au moment du versement.** C'est lui qui parie, pas
  le modèle : la règle de Constat est respectée, pas contournée.
- **PRISME score**, dans le plugin de calibration prévu par 0025, sur le type Prédiction
  livré par E11.

## Pourquoi le score reste dans PRISME

Le Brier agrégé par domaine et par horizon a besoin de **tout l'historique**. Une
extension de navigateur ne l'a pas, et deux historiques concurrents seraient pires que
pas de calibration du tout.

## Réserve

Le moment où l'on formule un pari est celui où l'on lit l'article, pas celui où l'on
ouvre PRISME. Si cette friction se révèle suffisante pour qu'aucune prédiction ne soit
jamais versée, il faudra un stockage temporaire dans l'extension avec versement différé.
Cela changerait la conception, pas la conclusion : le dépositaire reste le vault.

## Dépendances

Rien avant **E11**, qui livre le type Prédiction et ses champs. Le bouton côté Constat ne
peut pas être écrit avant de savoir ce que le vault attend.
