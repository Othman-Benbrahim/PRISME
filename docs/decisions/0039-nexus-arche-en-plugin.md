# 0039 · NEXUS-ARCHÊ en plugin — lecture assistée, garde-fous déterministes

- **Statut** : acceptée, en cours (lot 1 livré)
- **Écrite** : 2026-09-21

## Problème

NEXUS-ARCHÊ est un dispositif de lecture structurelle : seize cartes invariantes, en
double registre mathématique et anthropologique, avec un protocole de rigueur qui
impose un ancrage observable à chaque carte. Il existe comme skill — du texte, lu par
un modèle.

Le porter dans PRISME pose une question que le skill n'avait pas à trancher : **qui
produit la lecture, et qui la vérifie**.

## Décision

**Le modèle produit, le code vérifie, l'auteur valide.**

| Le modèle propose | Le code vérifie, hors ligne |
|---|---|
| 2 à 3 cartes candidates | jamais plus de 3, et existantes au catalogue |
| un ancrage par carte | **l'ancrage est une citation littérale du texte de situation** |
| les champs libres du bloc | champs présents, ordonnés, préfixes licites |
| la signature MÉMOIRE-Σ | alphabet, ordre des strates, comptes, statut |

### L'ancrage doit être une citation, pas une paraphrase

C'est le point qui tient tout le reste.

Le dispositif repose sur le test d'ancrage : une carte sans observation concrète est
déclarée inactive. Tant que l'auteur fournissait l'ancrage, ce test avait du mordant.
Si le **même modèle** propose la carte *et* rédige l'observation qui la justifie, le
test s'effondre : un modèle sait toujours produire une justification plausible pour ce
qu'il vient de choisir. On mesurerait sa fluidité, pas la structure de la situation.

L'ancrage rendu doit donc être un **extrait littéral** du texte soumis, vérifié par
comparaison de chaînes. Sans correspondance, la carte est refusée avant d'être montrée.
Le modèle ne peut plus inventer l'observation : il doit la **désigner**.

### Deux alphabets, jamais mêlés

MÉMOIRE-Σ ne remplace pas STÈLE, il le contient : son champ *Signature* est une chaîne
glyphique. Mais **Σ compresse une séance de travail**, là où NEXUS compresse une
situation analysée. Quinze glyphes leur sont communs avec des sens voisins et
distincts — `⊥` vaut LIMITE en Σ et SEUIL au catalogue.

La fiche porte donc deux choses séparées et étiquetées : la lecture NEXUS avec ses
cartes et ses ancrages, et un bloc Σ décrivant la séance, pour le report vers la session
suivante. Le valideur refuse tout glyphe du catalogue dans une signature Σ.

### Ce que cela coûte, et qu'on assume

Le plugin **n'est pas hors ligne** pour sa fonction centrale. Sans fournisseur d'IA
configuré, un parcours manuel complet reste offert — sinon l'exécutable distribuerait un
bouton mort. Le `README` du plugin le déclare.

Et les tests changent d'objet : on ne teste pas la justesse d'une lecture, à laquelle on
n'a pas accès. On teste **ce que le plugin fait quand le modèle répond mal** — quatre
cartes au lieu de trois, un ancrage introuvable dans le texte, une signature invalide,
un JSON tronqué. C'est là qu'est le risque, et c'est testable hors ligne avec un appel
simulé.

## Écarté

- **Tout déterministe, sans modèle** : l'arbre de distinction devait converger seul
  depuis un texte libre. Irréalisable sans compréhension du texte, et la contrainte
  « vert hors ligne » interdisait d'appeler un modèle dans les tests.
- **Reproduire les 10 situations du `test_log` en tests unitaires** : leurs sélections
  sont des interprétations, pas des réponses à des questions. Un tel test figerait la
  réponse dans la fixture et ne vérifierait plus rien. Elles deviennent un corpus
  d'**évaluation**, exécuté à la demande.
- **Porter les 16 cartes dans un module Python** : `references/cards.md` fait plus de
  20 000 caractères. Les données vivent dans `cartes.json` ; la fidélité se vérifie par
  comparaison plutôt que par relecture.
- **Une signature Σ décrivant la situation analysée** : il aurait fallu inventer une
  table de substances propre à NEXUS, donc une notation qui n'est plus Σ, et perdre la
  compatibilité avec les autres outils de l'auteur.
