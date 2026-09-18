# E2 — Index SQLite

## Objectif

Remplacer l'index en mémoire de la V1 par un index SQLite dérivé des `.md`, avec
recherche plein texte classée, et lever le plafond de 5 000 notes.
Décisions appliquées : [0010](../decisions/0010-index-sqlite-dans-le-profil.md),
[0011](../decisions/0011-double-granularite.md).

## Ce qui change

- **Base SQLite dans le profil** : `~/.prisme/index/<empreinte du chemin du vault>.db`,
  avec `vaults.json` pour retrouver quel vault correspond à quelle empreinte. Rien
  n'est écrit dans le vault, donc aucun conflit avec une synchronisation de fichiers.
  La base est toujours reconstructible : la supprimer ne perd rien.
- **Deux granularités** : une ligne par fichier (liens, tags, graphe) et une ligne
  par segment (recherche). Découpage par titres de niveau 1 à 3 ; notes sans titre
  regroupées par paragraphes vers 1 500 caractères ; sections longues recoupées
  au-delà de 4 000 caractères entre deux paragraphes ; un bloc de code n'est jamais
  coupé ; l'en-tête YAML n'est pas indexé.
- **Recherche FTS5** : classement BM25 (le titre de section pèse plus que le corps),
  insensible aux accents (« bayesienne » trouve « bayésienne »), par préfixe
  (« predi » trouve « prédiction »). Les extraits viennent de SQLite, avec le chemin
  du titre de section, et les termes trouvés sont surlignés. Repli automatique sur
  une recherche simple si le SQLite embarqué n'a pas FTS5.
- **Mise à jour incrémentale** : un fichier n'est relu que si sa date ou sa taille a
  changé, réindexé seulement si son contenu a changé, et à l'intérieur d'un fichier
  modifié seuls les segments dont l'empreinte a changé sont réécrits — les autres
  gardent leur identifiant, ce qui servira aux vecteurs de E7.
- **Réactivité** : une écriture faite dans PRISME est visible immédiatement ; une
  écriture faite ailleurs (Obsidian) au plus deux secondes après. Au-delà de
  5 000 notes, les vérifications passent en arrière-plan et la recherche répond avec
  ce qui est déjà indexé.
- **Reconstruction** (bouton dans Paramètres) : construite dans un fichier à part
  qui remplace l'ancien en une seule opération, une fois qu'aucune lecture n'est en
  cours. L'index en service n'est jamais à moitié écrit.
- **Graphe, backlinks, tags et `/api/files/find`** passent par l'index : plus de
  relecture de tout le vault à chaque appel, plus de plafond.
- **Résolution des liens** unifiée et déterministe : chemin relatif, puis fin de
  chemin exacte, puis nom sans extension ; à égalité, le chemin le plus court.
- **Questions de référence** : `evaluation/questions-reference.jsonl` et le vault
  `tests/fixtures/vault-eval/` mesurent la qualité de la recherche (10 cas).
- **Pour les plugins** : `ctx.search(texte)`.

Deux corrections au passage :
- les tags accentués étaient tronqués (`#méthode` devenait `#m`) ;
- `[[note]]` pouvait se résoudre vers `manote.md`, par correspondance partielle.

## Fichiers touchés

**Créés** : `prisme_core/index/` (`__init__.py`, `store.py`, `segmenter.py`,
`resolver.py`, `indexer.py`, `search.py`), `web/js` inchangés sauf ci-dessous,
`tests/test_e2_index.py`, `tests/fixtures/vault-eval/` (6 notes),
`evaluation/questions-reference.jsonl`, `evaluation/README.md`, ce fichier.

**Modifiés** : `routes/search.py` (réécrite), `routes/files.py`, `api.py`,
`app.py`, `markdown.py`, `web/index.html`, `web/js/search.js`,
`web/js/settings.js`, `web/css/core.css`, `tests/commun.py`,
`PLUGIN-DEVELOPMENT.md`, `README.md`, `docs/ARCHITECTURE.md`, `docs/RUPTURES.md`,
`docs/FEUILLE-DE-ROUTE.md`, `docs/decisions/0010`, `0011`, `README.md`.

**Supprimé** : `prisme_core/search_index.py`.

## Mesures

Sur un vault synthétique de **20 000 notes** (80 Mo de `.md`), sous Linux :

| Opération | Temps |
|---|---|
| Construction initiale (40 000 segments, 20 000 liens) | 11 s |
| Vérification sans changement | 0,10 s |
| Une note modifiée | 0,17 s |
| Recherche (mot rare) | 1 ms |
| Recherche (deux mots fréquents, 40 fichiers) | 190 à 260 ms |
| Graphe complet (20 000 nœuds) | 0,09 s |
| Reconstruction complète | 12 s |

**Coût en disque** : la base pèse environ trois fois la taille du vault
(259 Mo pour 80 Mo de notes). Le texte est stocké une fois dans les segments et
une fois dans l'index plein texte. À surveiller en E7, qui ajoutera les vecteurs.

## Tester

```powershell
python -m unittest discover -s tests -v
python prisme.py
```

64 tests, dont 27 pour E2 (découpage, résolution des liens, indexation
incrémentale, reconstruction, recherche, repli sans FTS5, routes) et les
10 questions de référence.

Vérifications manuelles :

1. `Ctrl+Shift+F` : chercher un mot sans ses accents, vérifier le surlignage et
   le titre de section affiché.
2. Paramètres : la ligne « Index de recherche » indique le nombre de notes, de
   segments et de liens résolus ; le bouton « Reconstruire l'index » la met à jour.
3. Modifier une note dans Obsidian, puis chercher dans PRISME : le changement
   doit apparaître en moins de deux secondes.
4. Ouvrir le graphe et les backlinks sur une note liée.

Vérifié ici dans un navigateur réel : recherche sans accents surlignée, recherche
par titre de section, ouverture d'un résultat, état et reconstruction de l'index,
tags accentués corrigés, graphe et backlinks.

## Limites connues

- La recherche est lexicale : elle ne trouve pas un synonyme. C'est l'objet de E7.
- Les segments changent d'identifiant dès que leur texte change ; l'identité
  stable d'un passage modifié (correspondance approchée) est prévue en E4.
- L'index pèse environ trois fois le vault.
- Une modification externe peut n'être vue qu'après deux secondes.

## Hors périmètre

Provenance et horloge d'enregistrement (E3), ENGRAM (E4), recherche sémantique (E7).
