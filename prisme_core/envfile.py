"""Chargement des fichiers .env (bibliotheque standard uniquement)."""
import os
from pathlib import Path

def load_env_file(path, override=False):
    """Charge un .env (lignes KEY=VALUE) dans os.environ. Stdlib uniquement.
    Ignore lignes vides et commentaires (#), tolere 'export KEY=val',
    retire les guillemets entourants, n'ecrase pas l'environnement reel par defaut.
    Retourne le nombre de cles chargees."""
    try:
        path = Path(path)
        if not path.exists():
            return 0
        n = 0
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1]
            if override or key not in os.environ:
                os.environ[key] = val
                n += 1
        return n
    except Exception as e:
        print(f"  ⚠ .env ({path}) non charge : {e}")
        return 0
