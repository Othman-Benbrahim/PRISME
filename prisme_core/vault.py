"""Acces au vault : racine autorisee, corbeille, instantanes, parcours des .md."""
import shutil
import time
from pathlib import Path

from flask import jsonify

from .config import rd_cfg

WELCOME = """# Bienvenue dans PRISME

Ceci est votre première note. Tout ce que vous écrivez ici vit dans un
simple fichier `.md` sur votre disque — aucun cloud, aucune base de données.

## Pour commencer

- `Ctrl+S` enregistre la note en cours
- `Ctrl+Shift+F` cherche dans toutes vos notes
- Écrivez [[une-autre-note]] pour créer un lien — il devient cliquable

Bonne écriture.
"""

def ensure_vault(path):
    """Cree le dossier de notes s'il n'existe pas, avec une note d'accueil."""
    p = Path(path).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    if not any(p.glob("*.md")):
        (p / "Bienvenue.md").write_text(WELCOME, encoding="utf-8")
    return p

SKIP_DIRS = {"node_modules", "AppData", "Library", ".git", ".trash",
             "__pycache__", "venv", ".venv", "Windows", "Program Files",
             "Program Files (x86)", "$RECYCLE.BIN", "OneDriveTemp"}

def vault_root():
    """Racine autorisee pour toute operation de fichier."""
    return Path(rd_cfg().get("workspace") or Path.home()).expanduser().resolve()

def safe_path(raw, must_exist=False):
    """Resout un chemin et REFUSE tout ce qui sort du vault.
    Un chemin relatif est interprete depuis la racine du vault.
    Leve PermissionError (hors vault) ou FileNotFoundError."""
    root = vault_root()
    p = Path(str(raw or "").strip()).expanduser()
    if not p.is_absolute():
        p = root / p
    try:
        p = p.resolve()
    except OSError:
        raise PermissionError("Chemin invalide")
    if p != root and root not in p.parents:
        raise PermissionError(
            "Hors de l'espace de travail (%s). Pour utiliser ce dossier, "
            "définissez-le comme espace de travail." % root)
    return p

def in_trash(p):
    return ".trash" in Path(p).parts

def to_trash(p):
    """Deplace vers <vault>/.trash/AAAA-MM-JJ/ au lieu de supprimer.
    Rien n'est jamais perdu par un simple clic — le menage se fait a la main."""
    trash = vault_root() / ".trash" / time.strftime("%Y-%m-%d")
    trash.mkdir(parents=True, exist_ok=True)
    target = trash / p.name
    i = 1
    while target.exists():
        target = trash / ("%s_%d%s" % (p.stem, i, p.suffix))
        i += 1
    shutil.move(str(p), str(target))
    return target

def _path_err(e):
    """Traduit une exception de chemin en reponse JSON."""
    if isinstance(e, PermissionError):
        return jsonify({"error": str(e)}), 403
    if isinstance(e, FileNotFoundError):
        return jsonify({"error": "Fichier ou dossier introuvable"}), 404
    return jsonify({"error": str(e)}), 500

SNAPSHOT_INTERVAL = 300         # 5 min : une sauvegarde par Ctrl+S ne spamme pas

_LAST_SNAP = {}

def snapshot(p):
    """Copie la version actuelle dans .trash/versions/ avant de l'ecraser.
    Limite a une copie toutes les SNAPSHOT_INTERVAL secondes par fichier."""
    try:
        if not p.exists() or p.is_dir() or in_trash(p):
            return None
        now  = time.time()
        last = _LAST_SNAP.get(str(p), 0)
        if now - last < SNAPSHOT_INTERVAL:
            return None
        d = vault_root() / ".trash" / "versions" / time.strftime("%Y-%m-%d")
        d.mkdir(parents=True, exist_ok=True)
        dest = d / ("%s_%s%s" % (p.stem, time.strftime("%H%M%S"), p.suffix))
        shutil.copy2(str(p), str(dest))
        _LAST_SNAP[str(p)] = now
        return dest
    except Exception:
        return None               # un instantane raté ne doit jamais bloquer une sauvegarde

MAX_SCAN = 5000

def iter_md(root):
    """Parcourt les .md en evitant les dossiers systeme et en plafonnant le total.
    Remplace rglob('*.md') : sur un dossier utilisateur entier, rglob gelait
    l'application pendant une minute au premier lancement."""
    root = Path(root)
    if not root.exists():
        return
    n = 0
    for p in root.rglob("*.md"):
        try:
            parts = p.relative_to(root).parts[:-1]
        except ValueError:
            continue
        if any(part in SKIP_DIRS or part.startswith(".") for part in parts):
            continue
        n += 1
        if n > MAX_SCAN:
            return
        yield p


def scoped_dir(raw=None):
    """Dossier demande par le client, ramene dans le vault (racine par defaut).
    Leve PermissionError s'il sort du vault."""
    raw = (raw or "").strip()
    return str(safe_path(raw) if raw else vault_root())
