# Plugin « Embeddings locaux » (ONNX)

## Objectif

Rendre la recherche sémantique d'E7 entièrement locale : un modèle e5 quantifié exécuté
par ONNX Runtime sur le processeur. **Ni les notes qu'on vectorise, ni les recherches
qu'on tape ne quittent la machine.** C'est la troisième voie prévue par la
[décision 0019](../decisions/0019-recherche-semantique.md), et la seule qui ne demande
de confiance à personne.

## Pourquoi un plugin et pas le cœur

Deux dépendances **compilées** — `onnxruntime` et `tokenizers` — plus un modèle de cent
à trois cents mégaoctets. Le cœur doit rester portable et tenir dans un exécutable ; un
plugin s'installe et se désinstalle. C'est l'exception assumée par 0019.

Sans ces bibliothèques, le plugin **se charge quand même** : seul le fournisseur se
déclare indisponible, en disant quoi installer. PRISME retombe alors sur la recherche
par mots, exactement comme pour n'importe quel fournisseur absent.

```
pip install -r plugins/embeddings-locaux/requirements.txt
```

## Ce que la construction a révélé dans E7

**Le contrat n'avait pas de rôle.** La famille e5 attend « query: » devant une requête
et « passage: » devant un document. Sans ces préfixes, tout fonctionne et la qualité
s'effondre, **sans que rien ne le signale** — le pire genre de défaut. Le contrat
n'exposait qu'un `vectoriser(textes)` identique dans les deux cas.

Ajouté : `Fournisseur.prefixe(role)` et `vectoriser_role(textes, role)`. Le cœur appelle
désormais avec `role="requete"` pour une recherche et `role="passage"` pour un segment.
Un fournisseur qui n'en a pas besoin — une API, Ollama — n'a rien à implémenter.

**La porte des plugins n'était pas dans l'API publique.** `enregistrer` vivait dans
`prisme_core.vecteurs`, alors que la règle d'E1 dit qu'un plugin n'importe que
`prisme_core.api`. Ajouté : `ctx.register_embeddings(classe)`, plus
`ctx.EmbeddingProvider` et `ctx.EmbeddingUnavailable`.

## Les trois détails qui décident de la qualité

Ils se trompent tous en silence, d'où les tests qui les surveillent.

1. **Les préfixes de rôle**, ci-dessus. Désactivables pour un modèle qui n'en veut pas.
2. **La moyenne pondérée par le masque d'attention.** Compter le remplissage fausse la
   moyenne des textes courts. Prendre le premier jeton (CLS) donne des vecteurs
   plausibles mais nettement moins bons.
3. **La normalisation**, pour que les cosinus soient comparables entre eux.

## Deux façons de fournir un modèle

| Voie | Ce qu'elle vaut |
|---|---|
| **Indiquer un dossier** contenant `model.onnx` et `tokenizer.json` | La plus sûre. Vous téléchargez depuis la source de votre choix, PRISME ne fait que lire. |
| **Télécharger depuis le catalogue** | Pratique. **PRISME ne vérifie pas ces adresses** : ce sont des dépôts publics qui peuvent changer. |

Garde-fous du téléchargement : **https uniquement**, plafond de taille, écriture sous un
nom temporaire puis renommage — une coupure ne laisse jamais un modèle à moitié écrit qui
semblerait valide — et empreinte SHA-256 affichée. « Épingler l'empreinte » la fige :
tout écart sera refusé au téléchargement suivant.

## « Essayer le modèle »

Le bouton vectorise trois phrases — deux proches, une sans rapport — et affiche les deux
cosinus avec un verdict. C'est le test qui dit tout : un modèle mal chargé, une
tokenisation cassée ou des préfixes absents se voient immédiatement, là où la recherche
se contenterait d'être médiocre sans rien dire.

## Fichiers

| Fichier | Rôle |
|---|---|
| `manifest.json` | api_version 1, permission `network` (téléchargement), bouton 🧠 Embeddings |
| `__init__.py` | Le fournisseur, les réglages, les routes |
| `moteur.py` | Tokenisation, inférence ONNX, moyenne masquée, normalisation |
| `modele.py` | Découverte, téléchargement vérifié, empreintes |
| `ui.html`, `ui.js`, `ui.css` | Panneau d'installation et de vérification |
| `requirements.txt` | `onnxruntime`, `tokenizers` — **du plugin, pas du cœur** |

Côté cœur : `vecteurs/contrat.py` (rôles), `api.py` (la porte),
`tests/fixtures/modele_minuscule.py`, `tests/test_plugin_embeddings.py` (25 tests).

## Ce qui est vérifié, et ce qui ne l'est pas

**Vérifié**, avec un modèle ONNX minuscule construit par les tests — un `Gather` de 4 Ko
dont les jetons d'un même thème partagent une direction. Il exerce exactement la même
chaîne que le vrai modèle :

- normalisation, dimension, lots de longueurs inégales, texte vide ;
- même thème nettement plus proche que thème opposé ;
- moyenne masquée : un texte d'un mot reste proche d'un texte de six mots du même thème ;
- les rôles changent bien l'encodage, et se désactivent ;
- refus des URL non-https, dossier incomplet signalé, empreinte calculée ;
- le fournisseur s'enregistre, se déclare local, vectorise le vault et la recherche par
  le sens trouve la bonne note ;
- modèle absent : indisponible annoncé, la recherche par mots continue.

**Non vérifié depuis ici** : le téléchargement réel et le comportement du vrai
`multilingual-e5-small`. L'environnement de développement n'a pas accès aux dépôts de
modèles. Les URL du catalogue sont données de mémoire et **doivent être vérifiées au
premier essai** — c'est précisément pourquoi « indiquer un dossier » est présenté comme
la voie principale, et pourquoi le bouton « Essayer le modèle » existe.

**Toujours pas essayé** : le build PyInstaller avec une bibliothèque compilée dans un
`--onefile`. C'est la question ouverte notée depuis E7.
