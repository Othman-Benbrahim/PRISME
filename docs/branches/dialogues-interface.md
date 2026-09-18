# Dialogues dans l'interface

## Objectif

Créer un fichier ouvrait un popup du navigateur (`prompt`), et les confirmations
passaient par `confirm`. Ces boîtes bloquent la page, ne se stylent pas, et
s'affichent en dehors de PRISME. Tout passe désormais par l'interface.

## Ce qui change

**Créer un fichier se fait dans l'explorateur.** Le bouton ＋ (barre du haut,
explorateur, ou onglets) insère une ligne de saisie en tête de la liste des fichiers :
on tape le nom, `Entrée` crée et ouvre la note, `Échap` annule. La note est créée dans
le dossier affiché, et le message de confirmation le rappelle.

**Deux fonctions remplacent les popups**, dans `web/js/dialogues.js` :
- `confirmer({titre, message, ok, danger})` → promesse vraie ou fausse ;
- `demanderTexte({titre, label, valeur, placeholder})` → promesse avec le texte ou `null`.

Elles s'affichent comme les autres fenêtres de PRISME, se ferment par `Échap`, et le
bouton dangereux est en rouge.

**Confirmations migrées** : suppression d'un fichier, fermeture d'un onglet non
enregistré, désinstallation d'un plugin, oubli d'une source ENGRAM, suppression et
restauration des presets (plugin Prompts), retrait d'un flux (plugin RSS).

**Un test garde-fou** parcourt tout le JavaScript du cœur et des plugins et échoue si
un `alert(`, `confirm(` ou `prompt(` réapparaît.

## Fichiers touchés

**Créés** : `web/js/dialogues.js`, `tests/test_dialogues.py`, ce fichier.
**Modifiés** : `web/index.html`, `web/css/editeur.css`, `web/js/editor.js`,
`explorer.js`, `tabs.js`, `plugin-manager.js`, `engram.js`,
`plugins/prompts/ui.js`, `plugins/rss/ui.js`, `docs/FEUILLE-DE-ROUTE.md`,
`docs/RUPTURES.md`.

## Tester

```powershell
python -m unittest discover -s tests -v
python prisme.py
```

116 tests. Vérifications manuelles : créer un fichier depuis les trois boutons ＋,
annuler avec `Échap`, supprimer un fichier, fermer un onglet modifié.

Vérifié ici dans un navigateur réel, en interceptant les boîtes de dialogue du
navigateur : aucune n'apparaît plus.

## Limites

- Le renommage utilisait déjà une saisie en ligne : il est inchangé.
- Les dialogues sont modaux : on ne peut pas naviguer dans le vault pendant qu'ils
  sont ouverts.
