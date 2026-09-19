# 0028 · Plusieurs racines de vault

- **Statut** : appliquée en E12
- **Écrite** : 2026-09-19

## Problème

Hors du vault, l'explorateur ne montre que les dossiers, jamais les fichiers, et
`safe_path` refuse toute lecture. C'était voulu : cette garde est la seule chose qui
empêche une page malveillante, un plugin ou un agent de lire le reste du disque.

Mais choisir un espace de travail à l'aveugle est pénible, et travailler sur deux
ensembles de notes distincts oblige à changer de vault et à tout réindexer.

## Décision

**Plusieurs racines déclarées**, au lieu d'une seule. Dans chacune, tout fonctionne
comme aujourd'hui : voir, ouvrir, éditer, indexer, chercher. **Hors de ces racines, rien
ne change** — dossiers seulement, aucune lecture.

La garde n'est pas affaiblie : elle porte sur une liste au lieu d'un chemin. Ce qui est
refusé aujourd'hui reste refusé, sauf ce que l'auteur a explicitement déclaré.

### Les agents ne suivent pas

`safe_path` sert à la fois l'interface, les plugins et la surface `/api/v1/`. Élargir
sans précaution élargirait pour tout le monde d'un coup. Donc :

- **Une clé d'agent reste bornée à la racine principale**, quelles que soient les racines
  déclarées.
- L'accès aux autres racines s'accorde **clé par clé**, comme le droit d'écriture (0018).
- La restriction est posée par la garde des agents, en un seul endroit, et `safe_path`
  l'honore partout. Oublier un appel échoue du côté restreint, jamais du côté permissif.

### Un index par racine

Chaque racine garde son propre index et son propre magasin de vecteurs — la machinerie
existante est déjà indexée par empreinte de chemin (0010). La recherche interroge
chaque racine et **fusionne par RRF**, comme E7 fusionne déjà lexical et sémantique : des
scores BM25 issus d'index différents ne sont pas comparables, des rangs le sont.

### Ce qui reste borné à une racine

Les `[[liens]]`, les backlinks, le graphe et les tags. Un lien ne traverse pas un vault :
deux racines sont deux ensembles de notes, pas un seul éclaté. Le jour où le contraire
serait souhaitable, ce sera une autre décision.

## Écarté

- **Lister les fichiers hors vault sans pouvoir les ouvrir** : montre sans donner, et ne
  répond pas au besoin de travailler sur plusieurs dossiers.
- **Un vault principal et un secondaire, pas plus** : rigide dès le troisième dossier.
- **Supprimer la garde** : elle est ce qui rend l'outil défendable.
