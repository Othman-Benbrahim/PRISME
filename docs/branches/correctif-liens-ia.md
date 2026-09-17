# Correctif — Liens IA et encodage des réponses IA

## Problèmes constatés

1. **Accents corrompus** (« crÃ©ation » au lieu de « création ») dans toutes les réponses
   IA diffusées au fil de l'eau, et pas seulement dans les suggestions de liens.
   Cause : quand un fournisseur répond en `text/event-stream` sans préciser le jeu de
   caractères, la bibliothèque `requests` suppose ISO-8859-1. Le texte UTF-8 était donc
   mal décodé côté serveur, avant d'arriver au navigateur. Le défaut existait depuis la V1.
2. **Suggestions de liens inutilisables** : une popup du navigateur (`alert`), à recopier
   à la main ; le JSON brut s'affichait dans le panneau « L'IA rédige » ; les propositions
   n'étaient pas vérifiées (note inexistante, passage déjà lié, le même lien partout).

## Corrections

- Les réponses des fournisseurs IA sont toujours décodées en UTF-8, en flux comme en
  réponse simple (`providers._chat_post`, `/api/ai/stream`).
- **Onglet « ✨ Liens » dans le panneau droit**, à côté de Structure et Backlinks.
  Le bouton 🔗 Liens IA ouvre le panneau (même s'il était replié) et lance l'analyse.
  Chaque proposition montre la note cible, le passage et la raison, avec trois actions :
  - **Insérer** : le passage devient `[[note|passage]]` (ou le lien est ajouté après le
    passage s'il contient de la mise en forme) ; la note passe en « modifiée », Ctrl+S
    pour enregistrer ;
  - **Voir** : sélectionne le passage dans l'éditeur ;
  - **Ignorer**.
- **Propositions vérifiées avant affichage** : note cible existante, passage présent
  mot pour mot, sur une ligne, hors d'un lien existant, sans doublon. Le nombre de
  propositions écartées est indiqué.
- Consigne au modèle resserrée : passage de 2 à 8 mots copiés exactement, cibles prises
  dans la liste, et « une liste vide est une bonne réponse » pour éviter les liens forcés.
- Les requêtes qui attendent du JSON (`nostream`) ne passent plus par l'affichage au fil
  de l'eau.
- La liste des notes candidates vient de tout le vault (et non plus du dossier affiché),
  jusqu'à 150 noms.

## Fichiers touchés

`prisme_core/providers.py`, `prisme_core/routes/ai.py`, `prisme_core/web/index.html`,
`web/js/link-suggest.js` (réécrit), `web/js/ai-stream.js`, `web/js/backlinks.js`,
`web/js/tabs.js`, `web/css/link-suggest.css` (nouveau),
`tests/test_correctif_encodage.py` (nouveau).

## Tester

```powershell
python -m unittest discover -s tests -v
python prisme.py
```

Le test d'encodage échoue sans le correctif (vérifié). Dans le navigateur, avec un faux
fournisseur qui répond sans jeu de caractères : accents corrects dans « Améliorer » et
dans les suggestions ; sur cinq propositions (dont une note inventée, un passage absent
et un passage déjà lié), deux affichées et trois écartées ; insertion des deux liens puis
enregistrement vérifiés dans le fichier.

À vérifier chez vous : 🔗 Liens IA sur une note réelle, puis « Améliorer » dans le
panneau « IA — Modifier ce fichier » pour contrôler les accents avec votre fournisseur.
