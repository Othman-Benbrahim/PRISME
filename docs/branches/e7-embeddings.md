# E7 — Recherche sémantique

## Objectif

Trouver par le sens, pas seulement par les mots : « anticipation » doit retrouver une
note qui parle de prédiction, même si le mot n'y figure pas. Décision appliquée :
[0019](../decisions/0019-recherche-semantique.md).

## Ce qui change

### Un contrat de fournisseur, deux implémentations dans le cœur

| Fournisseur | Ce que c'est |
|---|---|
| `api` | Tout service exposant `/embeddings` à la manière d'OpenAI |
| `ollama` | Une instance locale d'Ollama (`/api/embed`) |
| `onnx` | **Plugin**, pas le cœur : bibliothèque compilée et modèle de plusieurs dizaines de mégaoctets |

Un plugin enregistre le sien avec `@enregistrer` sur une sous-classe de `Fournisseur` —
c'est la porte prévue pour ONNX.

**Paramétrage séparé du chat.** On peut vouloir un modèle local pour écrire et une API
pour vectoriser, ou l'inverse. `emb_base_url`, `emb_modele`, `emb_api_key` sont distincts
de `base_url`, `model`, `api_key` ; la clé d'embeddings est chiffrée comme l'autre.

### Désactivée par défaut, et toujours visible

`emb_actif` vaut `False` au départ. Vectoriser, c'est parfois envoyer le texte de toutes
ses notes à un tiers : ça ne s'active pas par accident. Quand c'est actif, l'état est
affiché en permanence dans les Paramètres, et il dit lequel des deux cas s'applique :

> ● Active, en local — rien ne sort de votre machine. 3 421 segment(s) vectorisé(s)
> ⚠ ACTIVE, MODE DISTANT — le texte de vos notes est envoyé à … pour être vectorisé.

Lancer une vectorisation en mode distant demande une confirmation explicite.

### Deux étages, parce que le cosinus pur est trop lent

Comparer une requête à 60 000 segments en cosinus flottant prend **0,6 s** en Python pur
— mesuré, et trop lent pour une recherche qui répond pendant qu'on tape. D'où :

1. **Présélection binaire.** Chaque vecteur est réduit au signe de ses composantes, un
   bit par dimension, dans un entier Python. La distance de Hamming s'obtient par
   `(a ^ b).bit_count()`, exécuté en C : **4 ms pour 60 000 segments**.
2. **Rescoring flottant** des 400 meilleurs, en cosinus exact : **3 ms**.

La binarisation perd de la finesse, pas l'essentiel : elle écarte les 98 % de segments
sans rapport, et c'est le cosinus exact qui classe ce qui reste. **Aucune dépendance
ajoutée** — ni numpy, ni bibliothèque compilée, ni extension SQLite.

### Le magasin de vecteurs vit à part

Pas dans la base de l'index, et c'est délibéré. L'index se reconstruit tout seul dès que
`SCHEMA_VERSION` change ([0010](../decisions/0010-index-sqlite-dans-le-profil.md)) : il
est dérivé des `.md` et se refait en quelques secondes. Les vecteurs, eux, coûtent des
minutes et parfois de l'argent. Les loger dans la même base, ce serait les perdre à
chaque évolution des règles d'extraction.

Ils vivent donc dans `~/.prisme/vecteurs/<empreinte du vault>.db`, indexés par
**empreinte de segment** : un segment inchangé garde son vecteur quoi qu'il arrive à
l'index, et réindexer ne revectorise que ce qui a bougé.

**Un magasin, un modèle.** La signature `fournisseur:modèle:dimension` est enregistrée ;
en changer vide le magasin et déclenche une revectorisation annoncée.

### Fusion par RRF, et un plancher

Les deux classements — BM25 et cosinus — fusionnent par **Reciprocal Rank Fusion**
(k = 60). RRF ne compare pas un BM25 à un cosinus, qui ne sont pas commensurables : il ne
compare que des rangs, et récompense l'accord entre les deux recherches. Puis
diversification : trois passages par fichier au plus, pour qu'une seule note n'occupe pas
la page.

**Un plancher, parce que la recherche par le sens rend toujours quelque chose.** Une
recherche par mots qui ne trouve rien le dit ; une recherche vectorielle, elle, remonte
volontiers le moins mauvais candidat. Sans garde-fou, chercher « zèbre » dans un vault
qui n'en parle pas remonterait quarante notes au hasard. Deux coupes : un cosinus minimal
(0,30 par défaut, réglable — il dépend du modèle) et l'écart au meilleur résultat.

### La recherche ne tombe jamais

Fournisseur absent, mal configuré, en panne, vecteurs pas encore calculés : on rend le
résultat FTS5 seul, et on le dit dans la réponse. La barre de recherche affiche à chaque
fois ce qui a réellement tourné :

> Recherche par les mots et par le sens
> Recherche par les mots — *sens indisponible : aucun vecteur, lancez la vectorisation*

Chaque passage porte son origine : **sens**, **mots + sens**, ou rien pour une
correspondance de mots ordinaire. Un résultat trouvé par le sens seul ne doit pas passer
pour une correspondance littérale.

## Routes

| Route | Rôle |
|---|---|
| `GET /api/vecteurs/etat` | Ce qui est actif, où, avec quel modèle, combien de vecteurs |
| `POST /api/vecteurs/tester` | Sonde le fournisseur sans rien écrire (modèle, dimension, local ou distant) |
| `POST /api/vecteurs/vectoriser` | Met le magasin à jour (`{"fond": true}` pour ne pas bloquer) |
| `GET /api/vecteurs/progression` | Avancement, pour la barre d'état |
| `POST /api/vecteurs/vider` | Efface les vecteurs ; notes et index intacts |
| `POST /api/vecteurs/config` | Paramétrage des embeddings, sans toucher à celui du chat |
| `GET /api/search?mode=lexical` | Force la recherche par mots seule |

## Mesuré

Sur un vault de **20 000 notes** (80 000 segments, 60 000 empreintes distinctes),
fournisseur simulé sans réseau :

| Étape | Mesure |
|---|---|
| Construction de l'index | 7,2 s |
| Vectorisation | 12,5 s (hors temps du vrai fournisseur, qui dominera) |
| Base de vecteurs | 128 Mo |
| Présélection chargée en mémoire | 3 Mo, 0,07 s |
| **Recherche hybride** | **30 à 200 ms** |

Les 128 Mo sont le prix des vecteurs complets, nécessaires au rescoring exact. La
présélection, elle, tient en 3 Mo : c'est ce qui rend la recherche instantanée.

## Fichiers

| Fichier | Rôle |
|---|---|
| `prisme_core/vecteurs/contrat.py` | Interface `Fournisseur`, registre, signature |
| `prisme_core/vecteurs/fournisseurs.py` | `api` (compatible OpenAI) et `ollama` |
| `prisme_core/vecteurs/quantification.py` | Binarisation, Hamming, cosinus, RRF, diversification |
| `prisme_core/vecteurs/magasin.py` | Base des vecteurs, indexée par empreinte de segment |
| `prisme_core/vecteurs/vectorisation.py` | Mise à jour incrémentale, progression, état |
| `prisme_core/vecteurs/recherche.py` | Recherche sémantique, fusion, plancher, repli |
| `prisme_core/routes/vecteurs.py` | Les routes ci-dessus |
| `prisme_core/index/search.py` | `segments_lexicaux()` extrait pour la fusion |
| `prisme_core/web/js/vecteurs.js`, `css/vecteurs.css` | Paramétrage, état, badges d'origine |
| `tests/test_e7_vecteurs.py` | 32 tests |

## Ce qui reste

Le **plugin ONNX** : le cœur expose la porte (`enregistrer`), le plugin reste à écrire.
C'est aussi là que se posera la question jamais tranchée du **build PyInstaller** — une
bibliothèque compilée dans un `--onefile` n'a jamais été essayée sur ce projet.

## Vérifié

- 235 tests (`python -m unittest discover -s tests`), dont 32 pour cette étape.
- Mesures à l'échelle ci-dessus, sur 20 000 notes.
- Dans le navigateur : paramétrage, vectorisation, état affiché, recherche « anticipation »
  qui ne trouve rien par les mots et deux notes par le sens, badges d'origine, et
  « zèbre » qui ne remonte rien.
