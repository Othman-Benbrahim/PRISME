# 0019 · Recherche sémantique

- **Statut** : appliquée — E7 pour le cœur, `plugins/embeddings-locaux` pour la voie locale
- **Écrite** : 2026-09-16

**Retenu.** Interface « fournisseur d'embeddings » dans le cœur, avec trois voies :
plugin local ONNX Runtime + modèle e5 (exception assumée à la règle de dépendances :
bibliothèque compilée dans le plugin, modèle téléchargé à part) ; API compatible OpenAI
(`/embeddings`) avec paramétrage séparé du chat ; Ollama.

**Règles.** Pas de mélange de modèles dans un index (changement = revectorisation annoncée) ;
mode distant désactivé par défaut, avec avertissement ; mode actif toujours visible ;
fusion FTS5 + vecteurs par RRF (k = 60) puis diversification ; repli sur FTS5 seul en cas
d'absence ou de panne ; vecteurs réutilisés par empreinte de segment.

## Application en E7

Le contrat `Fournisseur` vit dans `prisme_core/vecteurs/contrat.py`, avec deux
implémentations — `api` (compatible OpenAI) et `ollama` — et un point d'enregistrement
pour les plugins, qui est la porte du fournisseur ONNX.

Les règles sont toutes en place : signature `fournisseur:modèle:dimension` enregistrée
avec les vecteurs, magasin vidé si elle change ; `emb_actif` à `False` par défaut avec
confirmation explicite avant tout envoi distant ; mode actif affiché en permanence ;
fusion RRF (k = 60) puis diversification ; repli sur FTS5 dès que le fournisseur manque ;
vecteurs réutilisés par empreinte de segment.

**Deux points non prévus par la décision, ajoutés à l'usage :**

- **Le magasin est une base séparée de l'index.** L'index se reconstruit tout seul à
  chaque changement de `SCHEMA_VERSION` ; les vecteurs, eux, coûtent cher. Les séparer
  évite de les perdre à chaque évolution des règles d'extraction.
- **Un plancher de pertinence.** La recherche par le sens rend toujours son moins mauvais
  candidat : sans cosinus minimal ni écart au meilleur résultat, une requête hors sujet
  remonterait quarante notes au hasard. Le seuil dépend du modèle, donc il est réglable.

**Performance.** Le cosinus flottant sur 60 000 segments prend 0,6 s en Python pur —
mesuré. La solution retenue, sans dépendance : présélection par quantification binaire et
distance de Hamming (`bit_count()`, 4 ms), puis rescoring flottant des 400 meilleurs
(3 ms). Recherche hybride mesurée entre 30 et 200 ms sur un vault de 20 000 notes.

## Le plugin local, et ce qu'il a révélé

Les trois voies existent désormais. Le plugin `embeddings-locaux` fait tourner un e5
quantifié par ONNX Runtime : ni les notes, ni les recherches ne quittent la machine.

Sa construction a montré **un trou dans le contrat d'E7** : il n'avait pas de notion de
rôle. La famille e5 attend « query: » devant une requête et « passage: » devant un
document, et sans ces préfixes tout fonctionne pendant que la qualité s'effondre, sans
qu'aucun signal ne l'indique. Ajouté : `prefixe(role)` et `vectoriser_role(textes, role)`.

Second manque : la porte des plugins vivait dans `prisme_core.vecteurs`, alors que la
règle d'E1 veut qu'un plugin n'importe que `prisme_core.api`. Ajouté :
`ctx.register_embeddings`.
