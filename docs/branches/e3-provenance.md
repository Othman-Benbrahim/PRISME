# E3 — Provenance

## Objectif

Chaque note produite par une machine porte son origine dans son en-tête ; une note
écrite à la main n'est touchée que le jour où quelque chose la cite. Décisions
appliquées : [0003](../decisions/0003-compatibilite-obsidian.md),
[0012](../decisions/0012-identifiants-poses-au-besoin.md),
[0022](../decisions/0022-horloges-des-objets.md).

## Ce qui change

**En-tête YAML, lisible par Obsidian**

| Champ | Contenu |
|---|---|
| `prisme_id` | Identifiant stable (12 caractères) |
| `prisme_type` | `note`, `synthese`, `reponse`, `import`, `source` |
| `prisme_enregistre_le` | Date d'entrée dans PRISME |
| `prisme_invalide_le` | Date de retrait, vide tant que la note est valable |
| `prisme_outil` | Ce qui a produit la note (plugin, action de l'éditeur) |
| `prisme_genere_par` | Modèle et service |
| `prisme_preset` | Preset de prompt utilisé |
| `prisme_sources` | Identifiants des notes citées, URLs pour les sources externes |
| `prisme_parent` | Note dont celle-ci dérive |
| `prisme_valide_du` / `prisme_valide_au` (+ `_etat`) | **Réservés**, non écrits pour l'instant |

`_etat` vaut `date`, `inconnue` ou `ouverte` : une date inconnue n'est pas une date
ouverte, et le champ date reste une vraie date pour Obsidian, qui n'admet qu'un type
par propriété.

**Un module de frontmatter sans dépendance.** Il n'écrit que les clés qu'il touche :
l'ordre des clés, les commentaires et le reste de l'en-tête sont préservés, et le
corps de la note n'est jamais modifié. Un en-tête jamais refermé est laissé intact.

**Estampillage au seul point qui crée des notes.** Tout ce qui produit une note passe
par `/api/files/save` ; la route accepte désormais un objet `provenance` et renvoie le
contenu estampillé. Migrés : synthèse de dossier, IA sur sélection, et les cinq
plugins qui enregistrent une note (ArXiv, DuckDuckGo, Context, OSINT, RSS).

**Identifiants posés au besoin.** Enregistrer une note qui cite `Alpha.md` pose un
`prisme_id` sur `Alpha.md` — et c'est le seul cas où PRISME modifie une note écrite à
la main. L'écriture se limite à l'en-tête, après un instantané **forcé** dans
`.trash/versions/` (le délai de 5 minutes ne s'applique pas à une écriture que
l'utilisateur n'a pas demandée).

**Index.** Nouvelle table `note_meta` : provenance de chaque note, recherche par
identifiant, liste des notes générées. Les tags de l'en-tête (`tags: [a, b]`) sont
désormais comptés comme les `#tags` du corps, comme dans Obsidian. Le schéma passe en
version 2 : **l'index existant se reconstruit tout seul au premier lancement**.

**Interface.** Un bouton dans la barre de l'éditeur indique si la note est écrite à la
main (ⓘ) ou produite par une machine (🤖). Il ouvre une fiche de provenance : type,
modèle, preset, date, et les sources cliquables qui ouvrent la note d'origine. Une
note sans en-tête l'explique au lieu d'afficher un tableau vide.

**Pour les plugins** : `ctx.write_note(chemin, contenu, provenance={...})`,
`ctx.note_meta(chemin)`, `ctx.ensure_id(chemin)`. Côté interface,
`saveGenerated(chemin, contenu, provenance)` remplace l'appel direct à
`/api/files/save`.

## Fichiers touchés

**Créés** : `prisme_core/frontmatter.py`, `prisme_core/provenance.py`,
`prisme_core/web/js/provenance.js`, `tests/test_e3_provenance.py`, ce fichier.

**Modifiés** : `prisme_core/api.py`, `vault.py`, `routes/files.py`,
`index/store.py`, `index/indexer.py`, `index/search.py`, `web/index.html`,
`web/css/editeur.css`, `web/js/tabs.js`, `web/js/synthesis.js`,
`web/js/ai-selection.js`, les `ui.js` des cinq plugins concernés, `tests/commun.py`,
`PLUGIN-DEVELOPMENT.md`, `docs/ARCHITECTURE.md`, `docs/RUPTURES.md`,
`docs/FEUILLE-DE-ROUTE.md`, `docs/decisions/0012`, `0022`, `README.md`.

## Tester

```powershell
python -m unittest discover -s tests -v
python prisme.py
```

84 tests, dont 20 pour E3 (frontmatter, estampillage, identifiants, routes, index).

Vérifications manuelles :

1. Ouvrir une note écrite à la main : le bouton ⓘ doit dire qu'elle n'a pas d'en-tête.
2. Poser une question au plugin Context sur une ou deux notes, puis enregistrer la
   réponse : la note créée doit s'ouvrir **avec son en-tête**, le bouton doit passer
   à 🤖, et les notes citées doivent avoir reçu un `prisme_id`.
3. Ouvrir la fiche de provenance et cliquer sur une source : elle doit s'ouvrir.
4. Ouvrir le vault dans Obsidian : les champs `prisme_*` doivent apparaître dans le
   panneau Propriétés, et le corps des notes doit être inchangé.

Vérifié ici dans un navigateur réel : note générée estampillée, onglet ouvert avec
l'en-tête, identifiant posé sur la seule note citée, fiche de provenance et
navigation vers la source, aucune erreur JavaScript.

## Limites connues

- Une note générée puis **modifiée à la main** garde sa provenance d'origine : PRISME
  ne trace pas encore les modifications successives.
- Les identifiants ne sont posés que sur les notes citées par une note générée. Rien
  ne parcourt le vault pour en poser partout, et c'est voulu.
- L'horloge du monde (`prisme_valide_du` / `prisme_valide_au`) est réservée mais
  inactive : elle servira aux décisions et aux prédictions.
- Si vous supprimez un `prisme_id` à la main, la note en recevra un nouveau la
  prochaine fois qu'elle sera citée, et l'ancienne référence deviendra orpheline.

## Hors périmètre

ENGRAM et l'ingestion (E4), file de validation et objet Source (E5).
