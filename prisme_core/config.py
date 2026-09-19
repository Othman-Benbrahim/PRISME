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
    # Racines supplementaires (docs/decisions/0028). La principale reste "workspace".
    "workspaces": [],
    "configured": False,
    # Recherche semantique (docs/decisions/0019). Parametree separement du chat :
    # on peut vouloir un modele local pour ecrire et une API pour vectoriser.
    # emb_actif reste False par defaut : vectoriser, c'est parfois envoyer le texte
    # de ses notes a un tiers, et ca ne s'active jamais sans un geste explicite.
    "emb_actif"      : False,
    "emb_fournisseur": "api",
    "emb_base_url"   : "",
    "emb_modele"     : "",
    "emb_api_key"    : "",
    "emb_seuil"      : 0.30,   # cosinus minimal pour qu'un resultat semantique compte
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
    cle_emb, etat_emb = secrets.reveal(stored.get("emb_api_key", ""))
    if etat_emb == "clair" and secrets.available() and cle_emb:
        stored["emb_api_key"] = secrets.protect(cle_emb)
        _write_raw(stored)
        etat_emb = "chiffree"
    cfg["emb_api_key"] = cle_emb
    cfg["emb_key_state"] = etat_emb
    return cfg


def wr_cfg(data):
    stored = _read_raw()
    data = dict(data or {})
    data.pop("key_state", None)
    data.pop("emb_key_state", None)
    if "api_key" in data:
        data["api_key"] = secrets.protect((data["api_key"] or "").strip())
    if "emb_api_key" in data:
        data["emb_api_key"] = secrets.protect((data["emb_api_key"] or "").strip())
    stored.update(data)
    _write_raw(stored)
