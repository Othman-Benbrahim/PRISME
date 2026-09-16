"""Premier lancement, configuration, diagnostic et liste des modeles."""
import json

from flask import Blueprint, jsonify, request
import requests as http

from ..config import DEFAULT_VAULT, rd_cfg, wr_cfg
from ..providers import _chat_post, _chat_url, _headers, needs_key
from ..vault import ensure_vault

bp = Blueprint("setup", __name__)

@bp.route("/api/setup/state", methods=["GET"])
def setup_state():
    c = rd_cfg()
    return jsonify({
        "configured": bool(c.get("configured")),
        "suggested_workspace": str(DEFAULT_VAULT),
        "workspace": c.get("workspace", ""),
    })

@bp.route("/api/setup", methods=["POST"])
def setup_save():
    d = request.json or {}
    ws = (d.get("workspace") or str(DEFAULT_VAULT)).strip()
    try:
        vault = ensure_vault(ws)
    except Exception as e:
        return jsonify({"error": "Dossier impossible à créer : %s" % e}), 400
    wr_cfg({
        "workspace" : str(vault),
        "base_url"  : (d.get("base_url") or "").strip().rstrip("/"),
        "api_key"   : (d.get("api_key") or "").strip(),
        "model"     : (d.get("model") or "").strip(),
        "configured": True,
    })
    return jsonify({"ok": True, "workspace": str(vault)})

@bp.route("/api/config", methods=["GET"])
def get_cfg():
    c = rd_cfg()
    return jsonify({**c, "api_key": "●●●" if c.get("api_key") else "", "has_key": bool(c.get("api_key"))})

@bp.route("/api/config", methods=["POST"])
def set_cfg(): wr_cfg(request.json); return jsonify({"ok": True})

@bp.route("/api/test", methods=["GET"])
def test_api():
    """Diagnostic — appelle l'API avec un prompt minimal et renvoie tout."""
    cfg = rd_cfg(); key = cfg.get("api_key")
    if needs_key(cfg): return jsonify({"ok": False, "step": "config", "error": "Pas de clé API"})
    url = _chat_url(cfg)
    info = {"url": url, "model": cfg.get("model"), "key_prefix": key[:8]+"…"}
    try:
        r = _chat_post(url,
            headers=_headers(cfg),
            json={"model": cfg["model"], "messages": [{"role":"user","content":"Dis bonjour"}],
                  "max_tokens": 30}, timeout=30)
        info["status"]     = r.status_code
        info["headers"]    = dict(r.headers)
        info["body_chars"] = len(r.text)
        info["body_start"] = r.text[:500]
        try:
            j = r.json()
            info["json_keys"] = list(j.keys()) if isinstance(j, dict) else None
            info["json"] = j if len(json.dumps(j)) < 1000 else "(tronqué)"
        except: info["json_error"] = "réponse non-JSON"
        return jsonify({"ok": r.status_code == 200, **info})
    except Exception as e:
        return jsonify({"ok": False, "step": "request", "error": f"{type(e).__name__}: {e}", **info})

@bp.route("/api/models", methods=["GET"])
def get_models():
    cfg = rd_cfg()
    if needs_key(cfg): return jsonify({"models": []})
    if not cfg.get("base_url"): return jsonify({"models": []})
    try:
        r = http.get(cfg["base_url"].rstrip("/")+"/models",
            headers=_headers(cfg), timeout=10)
        return jsonify({"models": [m["id"] for m in r.json().get("data", [])]})
    except: return jsonify({"models": []})
