"""Emplacements : ressources embarquees, dossier de l'application, profil utilisateur."""
import os
import shutil
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
WEB_DIR = PACKAGE_DIR / "web"

if getattr(sys, "frozen", False):
    # Executable PyInstaller : plugins/ et .env sont poses a cote de PRISME.exe
    HOME = Path(sys.executable).resolve().parent
else:
    # Depuis les sources : racine du depot
    HOME = PACKAGE_DIR.parent

PLUGINS_DIR = HOME / "plugins"

# Profil utilisateur. PRISME_DATA_DIR permet d'isoler un profil (tests, essais).
DATA_DIR = Path(os.getenv("PRISME_DATA_DIR") or (Path.home() / ".prisme")).expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)

LEGACY_DATA_DIR = Path.home() / ".secondbrain"


def import_legacy_config():
    """Reprend config.json de Second Brain V1 au premier lancement, sans rien modifier
    cote V1. Ne fait rien si PRISME a deja sa propre configuration."""
    target = DATA_DIR / "config.json"
    source = LEGACY_DATA_DIR / "config.json"
    if os.getenv("PRISME_DATA_DIR") or target.exists() or not source.exists():
        return False
    try:
        shutil.copy2(source, target)
        return True
    except OSError:
        return False
