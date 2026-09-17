"""Configuration utilisateur (profil ~/.prisme/).

La cle d'API est chiffree au repos (voir secrets.py). rd_cfg() la renvoie en
clair pour l'usage interne ; elle ne doit jamais etre renvoyee au navigateur.
"""
import json
import locale
from pathlib import Path

from . import secrets
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


def _read_raw():
    if not CFG_F.exists():
        return {}
    raw = CFG_F.read_bytes()
    # UTF-8 d'abord ; un config.json ecrit par la V1 peut etre dans la page de code locale
    for enc in dict.fromkeys(("utf-8", locale.getpreferredencoding(False) or "cp1252", "cp1252")):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, ValueError):
            continue
    return {}


def _write_raw(data):
    CFG_F.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def rd_cfg():
    stored = _read_raw()
    cfg = {**DEF_CFG, **stored}
    key, state = secrets.reveal(stored.get("api_key", ""))
    # Migration : une cle encore en clair est chiffree des que c'est possible
    if state == "clair" and secrets.available():
        stored["api_key"] = secrets.protect(key)
        _write_raw(stored)
        state = "chiffree"
    cfg["api_key"] = key
    cfg["key_state"] = state
    return cfg


def wr_cfg(data):
    stored = _read_raw()
    data = dict(data or {})
    data.pop("key_state", None)
    if "api_key" in data:
        data["api_key"] = secrets.protect((data["api_key"] or "").strip())
    stored.update(data)
    _write_raw(stored)
