# PRISME

> Mémoire locale, sourcée et interrogeable. Un prisme décompose un faisceau en spectre :
> PRISME décompose des sources brutes (notes, conversations, documents) en passages,
> objets et provenance, sans jamais perdre le faisceau d'origine.

**Statut : en construction.** Le code de départ est celui de Second Brain V1
(étiquette Git `base-v1`), considéré comme obsolète. PRISME le transforme étape par étape.

## Où en est le projet

La feuille de route est dans [`docs/FEUILLE-DE-ROUTE.md`](docs/FEUILLE-DE-ROUTE.md).
Chaque étape vit sur sa propre branche, documentée dans [`docs/branches/`](docs/branches/),
et n'entre dans `main` que par une pull request validée.

## Lancer PRISME

```powershell
pip install -r requirements.txt
python prisme.py
```

Le navigateur s'ouvre sur `http://localhost:5000`. Les tests se lancent avec
`python -m unittest discover -s tests -v`.

## Documents de référence

- [`docs/DECISIONS.md`](docs/DECISIONS.md) : les choix d'architecture et leurs raisons.
- [`docs/RUPTURES.md`](docs/RUPTURES.md) : tout ce qui change par rapport à la base V1.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) : où se trouve quoi dans le code.
- [`PLUGIN-DEVELOPMENT.md`](PLUGIN-DEVELOPMENT.md) : créer un plugin (guide provisoire).

## Principes

- Les fichiers `.md` du vault sont la seule source de vérité ; tout index se reconstruit.
- Chaque fragment reste relié à sa source (provenance).
- Réinjecter une même donnée ne crée pas de doublon (idempotence).
- Aucun fichier ne porte l'application entière.
- Le cœur reste léger ; ce qui est lourd vit dans des plugins optionnels.

## Licence

Voir `LICENSE`. Le code dérive de Second Brain V1, du même auteur.
