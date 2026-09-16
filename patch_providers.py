#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_providers.py — ajoute Gemini, Grok (xAI) et Anthropic aux fournisseurs.

  python patch_providers.py --dry-run
  python patch_providers.py

PREREQUIS : patch_onboarding.py doit avoir ete applique (ce script s'appuie
sur les helpers _headers / needs_key qu'il a installes).

Gemini et Grok exposent une couche OpenAI-compatible : ce sont deux entrees de
plus dans la liste deroulante, rien d'autre.

Anthropic n'est PAS OpenAI-compatible :
  - en-tete x-api-key + anthropic-version au lieu de Authorization: Bearer
  - endpoint /v1/messages au lieu de /chat/completions
  - le message system est un champ de premier niveau, pas un role
  - la reponse est {"content":[{"type":"text","text":...}]}, pas {"choices":[...]}
D'ou l'adaptateur _chat_post / _to_anthropic_body installe ci-dessous. Il est
transparent : les plugins continuent d'appeler _ai_call sans rien savoir.
"""
import argparse
import shutil
import sys
from pathlib import Path

MARKER = "# --- SB_PROVIDERS_PATCH ---"

# ═══════════════════════════════════════════════════════════════════════
#  Ancre : le bloc pose par patch_onboarding.py
# ═══════════════════════════════════════════════════════════════════════

OLD_HELPERS = '''def _is_local(url):
    return any(h in (url or "") for h in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]"))

def _headers(cfg):
    """Authorization uniquement si une cle existe — Ollama et LM Studio n'en veulent pas."""
    h = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        h["Authorization"] = "Bearer " + cfg["api_key"]
    return h'''

NEW_HELPERS = '''def _is_local(url):
    return any(h in (url or "") for h in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]"))

''' + MARKER + '''
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
        out["system"] = "\\n\\n".join(s for s in systems if s)
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
    return http.post(url, headers=headers, json=body, timeout=timeout, **kw)
''' + MARKER

# ── parse_chat_response : comprendre la reponse Anthropic ──────────────

OLD_PARSE = '''    # 1) JSON direct (non-streaming)
    try:
        d = json.loads(text)
        if isinstance(d, dict) and "choices" in d:'''

NEW_PARSE = '''    # 1) JSON direct (non-streaming)
    try:
        d = json.loads(text)
''' + MARKER + '''
        # Format Anthropic : {"content":[{"type":"text","text":"..."}]}
        if isinstance(d, dict) and isinstance(d.get("content"), list):
            parts = [b.get("text", "") for b in d["content"]
                     if isinstance(b, dict) and b.get("type") == "text"]
            if parts:
                return "".join(parts), None
        if isinstance(d, dict) and d.get("type") == "error" and isinstance(d.get("error"), dict):
            return None, "API: %s" % json.dumps(d["error"])[:300]
''' + MARKER + '''
        if isinstance(d, dict) and "choices" in d:'''

PY_EDITS = [
    (OLD_HELPERS, NEW_HELPERS, 1,
     "Helpers fournisseurs (_chat_url, _headers, adaptateur Anthropic)"),
    (OLD_PARSE, NEW_PARSE, 1,
     "parse_chat_response : format de reponse Anthropic"),
    ('cfg["base_url"].rstrip("/") + "/chat/completions"', '_chat_url(cfg)', 4,
     "URL de chat routee par fournisseur"),
    ('r = http.post(url,', 'r = _chat_post(url,', 4,
     "Appels de chat via l'adaptateur"),
]

FLEXIBLE = {
    'cfg["base_url"].rstrip("/") + "/chat/completions"',
    'r = http.post(url,',
}

# ═══════════════════════════════════════════════════════════════════════
#  ui.html : nouvelles entrees dans la liste des fournisseurs
# ═══════════════════════════════════════════════════════════════════════

OLD_CUSTOM = """  {id:'custom', label:'Autre (compatible OpenAI)', url:'', model:'', key:true, ph:'',
   help:'Tout service exposant /chat/completions au format OpenAI.'}"""

NEW_CUSTOM = """  {id:'anthropic', label:'Anthropic (Claude)', url:'https://api.anthropic.com/v1',
   model:'claude-sonnet-5', key:true, ph:'sk-ant-…',
   help:'Clé depuis console.anthropic.com. Dialecte propre à Anthropic, géré en interne.'},
  {id:'gemini', label:'Google Gemini', url:'https://generativelanguage.googleapis.com/v1beta/openai',
   model:'gemini-2.5-flash', key:true, ph:'AIza…',
   help:'Clé depuis Google AI Studio. Cliquez sur Tester pour charger la liste des modèles.'},
  {id:'grok', label:'xAI (Grok)', url:'https://api.x.ai/v1',
   model:'grok-4.6', key:true, ph:'xai-…',
   help:'Clé depuis console.x.ai.'},
  {id:'custom', label:'Autre (compatible OpenAI)', url:'', model:'', key:true, ph:'',
   help:'Tout service exposant /chat/completions au format OpenAI.'}"""


# ═══════════════════════════════════════════════════════════════════════
#  Moteur (identique a patch_onboarding.py)
# ═══════════════════════════════════════════════════════════════════════

def patch_python(src):
    report, out, failed = [], src, False
    for anchor, repl, expected, label in PY_EDITS:
        n = out.count(anchor)
        if n == 0:
            report.append(("✗", label, "ancre introuvable"))
            failed = True
            continue
        if n != expected and anchor not in FLEXIBLE:
            report.append(("✗", label, "%d occurrence(s), %d attendue(s)" % (n, expected)))
            failed = True
            continue
        out = out.replace(anchor, repl)
        report.append(("✓", label, "%d remplacement(s)" % n))
    return out, report, failed


def patch_html(src):
    if OLD_CUSTOM not in src:
        return src, [("✗", "Liste des fournisseurs", "entrée 'custom' introuvable")], True
    return src.replace(OLD_CUSTOM, NEW_CUSTOM), \
           [("✓", "Anthropic, Gemini et Grok ajoutés", "3 entrées")], False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(args.dir).resolve()
    py_f, html_f = root / "second_brain.py", root / "ui.html"

    for f in (py_f, html_f):
        if not f.exists():
            print("✗ Introuvable : %s" % f)
            return 1

    py_src, html_src = py_f.read_text(encoding="utf-8"), html_f.read_text(encoding="utf-8")

    if "SB_ONBOARD_PATCH" not in py_src:
        print("✗ patch_onboarding.py n'a pas été appliqué. Lancez-le d'abord.")
        return 1
    if MARKER in py_src:
        print("⚠ Le patch fournisseurs est déjà appliqué. Rien à faire.")
        return 0

    py_out, py_rep, py_fail = patch_python(py_src)
    html_out, html_rep, html_fail = patch_html(html_src)

    print("\n── second_brain.py " + "─" * 42)
    for mark, label, detail in py_rep:
        print("  %s %-52s %s" % (mark, label, detail))
    print("\n── ui.html " + "─" * 50)
    for mark, label, detail in html_rep:
        print("  %s %-52s %s" % (mark, label, detail))

    if py_fail or html_fail:
        print("\n✗ ABANDON — rien n'a été écrit.")
        return 2

    if args.dry_run:
        print("\n(--dry-run : aucun fichier modifié)")
        return 0

    shutil.copy2(py_f, py_f.with_suffix(".py.bak2"))
    shutil.copy2(html_f, html_f.with_suffix(".html.bak2"))
    py_f.write_text(py_out, encoding="utf-8")
    html_f.write_text(html_out, encoding="utf-8")

    print("\n✓ Patch appliqué.  Sauvegardes : second_brain.py.bak2, ui.html.bak2")
    print("  Vérifier :  python second_brain.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
