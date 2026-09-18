# Confort d'édition — numéros de ligne, annuler/rétablir, recherche dans la note

## Objectif

Trois demandes d'usage, indépendantes du format des notes. Elles sont dans leur
propre branche pour que la relecture d'E3 (provenance) reste lisible.

## Ce qui change

**1. Numéros de ligne, façon Notepad++**

- Une gouttière affiche le numéro de chaque ligne, et la ligne du curseur est mise
  en évidence.
- L'alignement tient même quand une ligne s'enroule : la gouttière reproduit le
  texte, invisible, avec la même largeur et le même retour à la ligne. Vérifié sur
  une note de 801 lignes : hauteur de la gouttière et hauteur du texte identiques
  au pixel près, défilement synchronisé.
- Une barre d'état affiche « Ligne N, col N », le nombre total de lignes et, s'il y
  a une sélection, le nombre de caractères sélectionnés.
- Au-delà de 6 000 lignes, la gouttière se désactive plutôt que de ralentir la
  frappe. Rendu mesuré : 20 ms pour 801 lignes.

**2. Annuler / rétablir**

- Deux flèches dans la barre de l'éditeur (↶ ↷), avec `Ctrl+Z`, `Ctrl+Y` et
  `Ctrl+Maj+Z`. Les boutons se grisent quand il n'y a rien à faire.
- **Un historique par fichier ouvert**, tenu par PRISME : celui du navigateur est
  perdu dès qu'on change d'onglet ou de mode, pas celui-ci. 200 pas au maximum,
  oubliés à la fermeture de l'onglet.
- La frappe au fil de l'eau est regroupée (450 ms) : annuler ne défait pas une
  lettre à la fois. Les insertions en bloc (réponse de l'IA, lien suggéré) forment
  un pas à part entière, donc une seule annulation suffit à les défaire.

**3. Recherche dans la note (`Ctrl+F`)**

- Barre de recherche dans l'éditeur : nombre d'occurrences, précédent, suivant
  (`F3` / `Maj+F3`), fermeture par `Échap`.
- **Insensible aux accents et à la casse**, comme la recherche globale : « prevision »
  trouve « prévision ».
- En mode Éditer, l'occurrence est sélectionnée dans le texte et l'éditeur défile
  jusqu'à elle. En mode Aperçu, les occurrences sont surlignées dans le rendu, sans
  toucher au Markdown source.
- **Ouvrir un résultat de la recherche globale ouvre la note et surligne directement
  le passage cherché** : c'est la demande d'origine — retrouver dans le texte ce que
  la recherche a trouvé.

## Fichiers touchés

**Créés** : `web/js/gutter.js`, `web/js/history.js`, `web/js/find-in-note.js`,
`web/css/editeur.css`, `tests/test_confort_editeur.py`, ce fichier.

**Modifiés** : `web/index.html` (gouttière, barre de recherche, barre d'état, boutons),
`web/js/editor.js`, `web/js/tabs.js`, `web/js/search.js`, `web/js/ai-file.js`,
`web/js/link-suggest.js`, `docs/ARCHITECTURE.md`, `docs/RUPTURES.md`,
`docs/FEUILLE-DE-ROUTE.md`.

Aucun changement côté serveur : l'étape ne touche à aucune route ni au format des notes.

## Tester

```powershell
python -m unittest discover -s tests -v
python prisme.py
```

Vérifications manuelles :

1. Ouvrir une note longue : les numéros doivent rester alignés sur les lignes qui
   s'enroulent, et suivre le défilement.
2. Taper du texte, puis `Ctrl+Z` plusieurs fois, puis `Ctrl+Y` : l'annulation doit
   porter sur des blocs de frappe, pas sur des lettres isolées.
3. Changer d'onglet puis revenir : l'historique de chaque fichier doit être propre
   à ce fichier.
4. `Ctrl+F`, chercher un mot sans ses accents, naviguer avec `F3`, basculer en
   Aperçu : les occurrences doivent y être surlignées.
5. `Ctrl+Maj+F`, chercher un mot, ouvrir un résultat : la note s'ouvre avec le
   passage sélectionné.

Vérifié ici dans un navigateur réel (Chromium) : aucune erreur JavaScript, gouttière
alignée et synchronisée sur 801 lignes, annuler/rétablir sur plusieurs pas et au
clavier, recherche sans accents en mode Éditer et en mode Aperçu, ouverture d'un
résultat de recherche globale avec surlignage.

## À savoir

- `Ctrl+F` remplace la recherche du navigateur dans la page. `Ctrl+Maj+F` reste la
  recherche globale dans le vault.
- `Ctrl+Z` n'est plus l'annulation native du navigateur : c'est l'historique de
  PRISME qui répond, y compris après un changement d'onglet.
- L'historique vit en mémoire : fermer PRISME l'efface. Les versions précédentes
  d'un fichier restent disponibles dans `.trash/versions/` du vault.
