# Créer un plugin PRISME

Guide de l'API des plugins, **version 1** (`api_version: 1`).
Les plugins écrits pour Second Brain V1 ne se chargent plus : voir « Migrer un plugin V1 » en fin de guide.

## Principe

Un plugin est un dossier dans `plugins/`. Son nom de dossier est son identifiant.

```
plugins/mon-plugin/
├── manifest.json     obligatoire
├── __init__.py       facultatif : routes et hooks côté serveur
├── ui.html           facultatif : fragment HTML ajouté à la page (modales…)
├── ui.js             facultatif : chargé comme fichier séparé
├── ui.css            facultatif : chargé comme fichier séparé
└── .env              facultatif : variables de secours, jamais versionné
```

Le plugin n'importe **que** `prisme_core.api`. Tout le reste de `prisme_core` est interne
et peut changer sans préavis.

## Le manifest

```json
{
  "id": "mon-plugin",
  "name": "Mon plugin",
  "version": "1.0.0",
  "api_version": 1,
  "description": "Ce que fait le plugin, en une phrase.",
  "author": "Votre nom",
  "permissions": ["network", "vault_write", "secrets"],
  "secrets": [
    {"name": "MON_SERVICE_KEY", "label": "Clé du service", "optional": false}
  ],
  "buttons": [
    {"panel": "toolbar", "label": "🧪 Mon plugin", "title": "Info-bulle", "onclick": "openMonPlugin()"}
  ]
}
```

| Champ | Règle |
|---|---|
| `id` | Obligatoire, identique au nom du dossier : minuscules, chiffres, `-` et `_`, 40 caractères au plus |
| `api_version` | Obligatoire, `1` |
| `name` | Obligatoire |
| `permissions` | Parmi `network`, `vault_write`, `secrets`, `processes` |
| `secrets` | Noms en `MAJUSCULES_SOULIGNÉES` ; exige la permission `secrets` |
| `buttons` | Boutons ajoutés à la barre de l'éditeur (`panel: "toolbar"`) |

**Les permissions informent, elles ne confinent pas.** Elles sont affichées avant
l'installation et vérifiées par les fonctions de `ctx` qui les concernent
(`write_note`, `secret`). Mais un plugin est du code Python exécuté avec les droits de
PRISME : rien ne l'empêche d'importer `os` ou `requests` directement. Déclarez
honnêtement ce que fait votre plugin.

| Permission | Signification |
|---|---|
| `network` | Accède à Internet |
| `vault_write` | Crée ou modifie des notes (obligatoire pour `ctx.write_note`) |
| `secrets` | Lit des secrets (obligatoire pour `ctx.secret`) |
| `processes` | Lance des programmes installés sur la machine |

## Le serveur : `register(ctx)`

```python
from flask import jsonify, request


def register(ctx):

    @ctx.route("/recherche", methods=["POST"])
    def recherche():
        probleme = ctx.ai_unavailable()
        if probleme:
            return jsonify({"error": probleme}), 400
        question = (request.json or {}).get("question", "")
        texte, erreur = ctx.ai_call([
            {"role": "system", "content": "Réponds en français."},
            {"role": "user", "content": question},
        ], max_tokens=800)
        if erreur:
            return jsonify({"error": erreur}), 502
        return jsonify({"reponse": texte})

    @ctx.on("note_saved")
    def note_enregistree(path, origin, **_):
        ctx.log(f"{path} enregistrée par {origin}")
```

Les routes sont servies sous **`/api/plugins/<id>/`** : la route `/recherche` ci-dessus
répond à `POST /api/plugins/mon-plugin/recherche`. Les variables d'URL de Flask
fonctionnent (`@ctx.route("/note/<nom>")`). Toutes les routes exigent le jeton de
session, ajouté automatiquement par la page.

### Ce que fournit `ctx`

| Membre | Rôle |
|---|---|
| `ctx.id`, `ctx.name`, `ctx.directory`, `ctx.manifest` | Identité du plugin |
| `ctx.route(regle, methods=[...])` | Déclare une route (décorateur) |
| `ctx.url(sous_chemin)` | URL complète d'une route du plugin |
| `ctx.config()` | Configuration générale, **sans** la clé d'API |
| `ctx.ai_unavailable()` | `None` si l'IA est utilisable, sinon un message à afficher |
| `ctx.ai_call(messages, max_tokens=2000, temperature=0.5, timeout=120)` | Appel au modèle configuré ; renvoie `(texte, erreur)` |
| `ctx.vault_root()` | Racine du vault |
| `ctx.safe_path(chemin)` | Résout un chemin et lève `PermissionError` s'il sort du vault |
| `ctx.iter_notes(dossier=None)` | Parcourt les `.md` du vault |
| `ctx.read_note(chemin)` | Lit une note du vault |
| `ctx.write_note(chemin, contenu)` | Écrit une note, avec instantané de l'ancienne version ; déclenche `note_saved` ou `note_created` |
| `ctx.data_dir()` | Dossier privé du plugin : `~/.prisme/plugins/<id>/` |
| `ctx.adopt_legacy_file(nom)` | Reprend une seule fois `~/.secondbrain/<nom>` dans `data_dir()` |
| `ctx.secret(nom)` | Secret déclaré : coffre chiffré de PRISME, puis variable d'environnement |
| `ctx.on(evenement)` | Abonne une fonction à un événement (décorateur) |
| `ctx.log(message)` | Écrit dans la console de PRISME |

Fonctions utilitaires importables : `from prisme_core.api import extract_link_refs, resolve_ref, extract_tags`.

**Tout chemin reçu du navigateur passe par `ctx.safe_path`.** Une `PermissionError`
non rattrapée est convertie en réponse 403.

### Hooks

| Événement | Arguments |
|---|---|
| `note_saved` | `path`, `origin` |
| `note_created` | `path`, `origin` |
| `note_renamed` | `path`, `old_path`, `origin` |
| `note_deleted` | `path`, `origin` |

`origin` vaut `"editeur"` ou l'identifiant du plugin qui a écrit. Un plugin n'est jamais
notifié de ses propres écritures. Acceptez toujours `**_` : de nouveaux arguments
pourront s'ajouter.

Les hooks sont **synchrones** : l'éditeur attend leur fin avant de confirmer. Chaque
hook dispose de **3 secondes**. Au-delà, PRISME n'attend plus et signale le plugin ;
une exception est aussi signalée sans bloquer la sauvegarde. Python ne sait pas
interrompre un fil d'exécution : un hook trop lent continue en arrière-plan. Pour un
traitement long, lancez votre propre fil depuis le hook et rendez la main.

### Secrets

Déclarez chaque secret dans le manifest. L'utilisateur le saisit dans
**🧩 Plugins** ; sous Windows, il est chiffré (DPAPI). `ctx.secret(nom)` lit
d'abord ce coffre, puis la variable d'environnement de même nom (fichier `.env` du
plugin ou de PRISME). Lisez un secret **au moment de l'utiliser**, pas à l'import du
module : il peut être saisi après le démarrage.

## L'interface : `ui.html`, `ui.js`, `ui.css`

- `ui.html` est inséré dans la page ; `ui.js` et `ui.css` sont chargés **chacun comme
  un fichier**. Une erreur dans votre `ui.js` n'affecte que votre plugin.
- Les déclarations globales (`var`, `let`, `const`, `function`) partagent l'espace
  global avec le cœur et les autres plugins : préfixez vos noms (`monPluginOuvrir`).
- Appelez vos routes par leur URL complète : `fetch('/api/plugins/mon-plugin/recherche', ...)`.
- Fonctions du cœur utilisables : `$(id)`, `post(url, donnees)`, `esc(texte)`,
  `toast(message, duree)`, `openJson(url)`, et les variables `ACTIVE` (chemin de la note
  ouverte) et `CUR_DIR` (dossier affiché).
- Modales : `<div id="m-mon-plugin" class="ov"><div class="mb">…</div></div>`, ouvertes en
  ajoutant la classe `on`.
- Un attribut `data-sys-prompt-target` sur un `<textarea>` y ajoute le sélecteur de
  prompts du plugin Prompts, s'il est actif.

## Installer, activer, distribuer

- **Pendant le développement** : posez le dossier dans `plugins/` et redémarrez PRISME.
- **Distribution** : une archive ZIP contenant le dossier du plugin, à la racine ou
  dans un dossier unique (les archives de release GitHub conviennent). Taille : 20 Mo
  compressés, 100 Mo décompressés au plus.
- L'utilisateur l'installe depuis **🧩 Plugins**, par fichier ou par adresse `https://`,
  après un écran qui montre le manifest, les permissions et l'empreinte SHA-256.
- Activer ou désactiver ne demande pas de redémarrage (la page doit être rechargée
  pour afficher ou retirer l'interface). **Mettre à jour** un plugin déjà chargé
  demande un redémarrage.
- PRISME mémorise l'empreinte du dossier installé et signale un plugin modifié après
  coup.

## Migrer un plugin V1

| Second Brain V1 | PRISME, API v1 |
|---|---|
| `from second_brain import _ai_call` | supprimé : utiliser `ctx.ai_call` |
| `def register(app, rd_cfg):` | `def register(ctx):` |
| `@app.route("/api/mon-plugin/x")` | `@ctx.route("/x")` → `/api/plugins/<id>/x` |
| `_ai_call(rd_cfg(), msgs, temp=0.5)` | `ctx.ai_call(msgs, temperature=0.5)` |
| `if not cfg.get("api_key")` | `ctx.ai_unavailable()` (gère aussi les modèles locaux sans clé) |
| `rd_cfg()["workspace"]` | `ctx.vault_root()` |
| `Path.home() / ".secondbrain" / "x.json"` | `ctx.adopt_legacy_file("x.json")` |
| `os.getenv("MA_CLE")` | `ctx.secret("MA_CLE")` + déclaration dans le manifest |
| `fetch('/api/mon-plugin/x')` | `fetch('/api/plugins/<id>/x')` |
| `window.open('/api/...')` | `openJson('/api/...')` (le jeton est ajouté) |
| manifest sans `id` ni `api_version` | ajouter `id`, `api_version: 1`, `permissions` |

Les six plugins fournis avec PRISME ont été migrés ainsi : leur code est un exemple complet.
