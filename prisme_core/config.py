"""Configuration utilisateur (profil ~/.prisme/)."""
import json
from pathlib import Path

from .paths import DATA_DIR

DATA  = DATA_DIR
CFG_F = DATA / "config.json"

DEFAULT_VAULT = Path.home() / "Documents" / "PRISME"

DEF_CFG = {
    "api_key"   : "",
    "model"     : "",
    "base_url"  : "",
    "workspace" : str(DEFAULT_VAULT),
    "configured": False,
}

def rd_cfg():
    if CFG_F.exists():
        try: return {**DEF_CFG, **json.loads(CFG_F.read_text())}
        except: pass
    return {**DEF_CFG}

def wr_cfg(data):
    c = rd_cfg(); c.update(data)
    CFG_F.write_text(json.dumps(c, indent=2, ensure_ascii=False))
