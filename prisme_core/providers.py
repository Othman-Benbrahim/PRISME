"""Fournisseurs IA : OpenAI-compatibles et Anthropic, appel generique."""
import json

import requests as http

def _is_local(url):
    return any(h in (url or "") for h in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]"))

ANTHROPIC_VERSION = "2023-06-01"

def _is_anthropic(cfg):
    """Anthropic parle son propre dialecte — detecte sur l'URL."""
    return "api.anthropic.com" in (cfg.get("base_url") or "")

def _chat_url(cfg):
    base = (cfg.get("base_url") or "").rstrip("/")
    return base + ("/messages" if _is_anthropic(cfg) else "/chat/completions")

def _headers(cfg):
    """En-tetes selon le fournisseur.
    - Anthropic : x-api-key + anthropic-version
    - tous les autres : Authorization: Bearer, et RIEN si la cle est vide
      (Ollama et LM Studio n'en veulent pas)."""
    if _is_anthropic(cfg):
        h = {"content-type": "application/json", "anthropic-version": ANTHROPIC_VERSION}
        if cfg.get("api_key"):
            h["x-api-key"] = cfg["api_key"]
        return h
    h = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        h["Authorization"] = "Bearer " + cfg["api_key"]
    return h

def _to_anthropic_body(body):
    """Convertit un corps OpenAI en corps Anthropic.
    Les messages 'system' deviennent un champ de premier niveau ; max_tokens
    est obligatoire cote Anthropic ; 'stream' n'a pas le meme sens et saute."""
    out = {k: v for k, v in (body or {}).items() if k not in ("stream", "messages")}
    systems, msgs = [], []
    for m in (body or {}).get("messages", []):
        if m.get("role") == "system":
            systems.append(m.get("content", ""))
        else:
            msgs.append({"role": m.get("role", "user"), "content": m.get("content", "")})
    if systems:
        out["system"] = "\n\n".join(s for s in systems if s)
    if not msgs:
        msgs = [{"role": "user", "content": " "}]
    if msgs[0]["role"] != "user":          # Anthropic exige que ca commence par user
        msgs.insert(0, {"role": "user", "content": " "})
    out["messages"] = msgs
    out.setdefault("max_tokens", 2000)
    return out

def _chat_post(url, headers=None, json=None, timeout=120, **kw):
    """Remplace http.post pour les appels de chat : convertit le corps si besoin.
    Transparent pour tous les fournisseurs OpenAI-compatibles."""
    body = json or {}
    if headers and "anthropic-version" in headers:
        body = _to_anthropic_body(body)
    r = http.post(url, headers=headers, json=body, timeout=timeout, **kw)
    # Les API de chat repondent en UTF-8. Sans charset annonce, requests suppose
    # ISO-8859-1 pour text/* : les accents devenaient "Ã©".
    r.encoding = "utf-8"
    return r

def needs_key(cfg):
    """True si une cle est indispensable : service distant sans cle configuree."""
    return not cfg.get("api_key") and not _is_local(cfg.get("base_url", ""))

def parse_chat_response(text):
    """Parse une réponse chat completion — gère le JSON simple ET le streaming SSE."""
    # 1) JSON direct (non-streaming)
    try:
        d = json.loads(text)
# --- SB_PROVIDERS_PATCH ---
        # Format Anthropic : {"content":[{"type":"text","text":"..."}]}
        if isinstance(d, dict) and isinstance(d.get("content"), list):
            parts = [b.get("text", "") for b in d["content"]
                     if isinstance(b, dict) and b.get("type") == "text"]
            if parts:
                return "".join(parts), None
        if isinstance(d, dict) and d.get("type") == "error" and isinstance(d.get("error"), dict):
            return None, "API: %s" % json.dumps(d["error"])[:300]
# --- SB_PROVIDERS_PATCH ---
        if isinstance(d, dict) and "choices" in d:
            c = d["choices"][0]
            if "message" in c and "content" in c["message"]: return c["message"]["content"], None
            if "delta"   in c and "content" in c["delta"]:   return c["delta"]["content"], None
        if isinstance(d, dict) and "error" in d:
            return None, f"API: {json.dumps(d['error'])[:300]}"
    except ValueError: pass

    # 2) Streaming SSE : concatène tous les chunks
    parts = []
    for line in text.split("\n"):
        line = line.strip()
        if not line.startswith("data:"): continue
        body = line[5:].strip()
        if body in ("", "[DONE]"): continue
        try:
            chunk = json.loads(body)
            if "choices" in chunk and chunk["choices"]:
                ch = chunk["choices"][0]
                if "delta" in ch and ch["delta"].get("content"):
                    parts.append(ch["delta"]["content"])
                elif "message" in ch and ch["message"].get("content"):
                    parts.append(ch["message"]["content"])
        except ValueError: continue
    if parts: return "".join(parts), None
    return None, f"Aucun contenu extractible. Début reçu: {text[:300]}"

def _ai_call(cfg, msgs, max_tokens=2000, temp=0.5, timeout=120):
    """
    Appel IA générique — exposé aux plugins.
    Retourne (content, error) où l'un des deux est None.
    """
    key = cfg.get("api_key")
    if needs_key(cfg): return None, "Clé API manquante"
    url = _chat_url(cfg)
    try:
        r = _chat_post(url,
            headers=_headers(cfg),
            json={"model": cfg["model"], "messages": msgs,
                  "temperature": temp, "max_tokens": max_tokens, "stream": False}, timeout=timeout)
    except http.exceptions.ReadTimeout:
        return None, (f"Timeout après {timeout}s. Le modèle prend trop de temps à répondre. "
                      f"→ Essayez un modèle plus rapide (gpt-4o-mini) ou réduisez la sortie.")
    except Exception as e:
        return None, f"Réseau : {type(e).__name__}: {str(e)[:200]}"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:300]}"
    if not r.text.strip():
        return None, "Réponse vide"
    return parse_chat_response(r.text)
