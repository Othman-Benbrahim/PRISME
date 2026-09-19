# 0030 · Dépendances compilées gelées dans l'exécutable

- **Statut** : acceptée, à appliquer (E9)
- **Écrite** : 2026-09-19

## Problème

La version publique sera un exécutable : l'utilisateur extérieur n'installera pas Python.
Or PRISME n'exécute **jamais** `pip` — le gestionnaire de plugins installe des fichiers,
pas des bibliothèques. Un plugin à dépendances tierces se contente de constater leur
absence et d'afficher une instruction.

Cette instruction est `pip install onnxruntime tokenizers`. Un utilisateur de l'exécutable
ne peut pas la suivre : il n'a pas de Python. Le plugin des embeddings locaux serait donc
visible, installable, et définitivement inutilisable — la pire des trois situations.

Les six autres plugins fournis n'utilisent que la bibliothèque standard et ne posent aucun
problème. Le sujet ne concerne que celui-là, aujourd'hui.

## Décision

**Geler `onnxruntime` et `tokenizers` dans l'exécutable**, par imports cachés PyInstaller.
Le plugin les trouve déjà importables ; il n'a rien à installer et son code ne change pas.

Coût assumé : environ 150 Mo d'exécutable, y compris pour qui n'activera jamais les
embeddings locaux.

### Ce qui ne change pas

La disposition est déjà celle du code depuis E8, dans `paths.py` :

```python
if getattr(sys, "frozen", False):
    HOME = Path(sys.executable).resolve().parent   # plugins/ et .env à côté de PRISME.exe
else:
    HOME = PACKAGE_DIR.parent
PLUGINS_DIR = HOME / "plugins"
```

Un exécutable, un dossier `plugins/` à côté, et le profil (`~/.prisme/`) à part — config,
index, vecteurs, état des plugins. Un exécutable déplacé ou mis à jour n'emporte pas les
données.

Le modèle e5 (environ 120 Mo) reste **hors** de l'exécutable : le plugin le télécharge
dans le profil, avec empreinte vérifiée. L'y inclure doublerait la taille et figerait le
choix du modèle.

### `--onedir`, pas `--onefile`

`--onefile` décompresse tout dans un dossier temporaire à chaque lancement : lent sur une
archive de cette taille, et les bibliothèques compilées échouent parfois à se charger
depuis là. `--onedir` avec un installeur donne le même confort sans ce risque.

## Écarté

- **Deux téléchargements** (`PRISME.exe` léger et `PRISME-embeddings.exe`) : deux
  artefacts à construire, à tester et à expliquer, pour une économie de place.
- **Ne rien geler** et limiter l'exécutable aux fournisseurs par clé API : ce serait
  renoncer, dans la version publique, à la seule configuration où rien ne sort de la
  machine — c'est-à-dire à un argument central du projet.
- **Embarquer un Python avec son `pip`** : l'exécutable reste petit et les plugins gardent
  leur autonomie, mais la complexité de construction est sans rapport avec le problème
  réel, qui ne concerne aujourd'hui qu'un seul plugin.

## À vérifier au build

Que `onnxruntime` charge bien depuis l'exécutable gelé. C'est le point qui peut invalider
cette décision, et il ne se voit qu'en construisant.
