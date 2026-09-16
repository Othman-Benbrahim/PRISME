#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_streaming.py — affiche la reponse de l'IA au fil de l'eau.

  python patch_streaming.py --dry-run
  python patch_streaming.py

PROBLEME CORRIGE
  Tous les appels partaient avec "stream": False. Avec une API rapide c'est
  tolerable ; avec Ollama sur CPU, l'interface reste figee 2 a 5 minutes sans
  le moindre signe de vie, et l'utilisateur croit l'application plantee.

APPROCHE
  Serveur : nouvelle route /api/ai/stream qui relaie le flux SSE du
  fournisseur (formats OpenAI ET Anthropic).
  Client  : la fonction globale post() est enveloppee. Tout appel a
  '/api/ai' passe par le flux ; les autres routes ne changent pas. Les
  sites d'appel existants ne sont PAS modifies — ils recoivent toujours
  {response: "..."} une fois le flux termine.
  En cas d'echec du flux, repli automatique sur l'ancienne route.

PREREQUIS : patch_onboarding.py et patch_providers.py appliques.
"""
import argparse
import shutil
import sys
from pathlib import Path

MARKER = "SB_STREAM_PATCH"

# ═══════════════════════════════════════════════════════════════════════
#  Serveur : route de streaming, inseree avant /api/files
# ═══════════════════════════════════════════════════════════════════════

OLD_ANCHOR = '@app.route("/api/files", methods=["GET"])'

NEW_ROUTE = '''# --- ''' + MARKER + ''' ---
def _sse(obj):
    return "data: " + json.dumps(obj, ensure_ascii=False) + "\\n\\n"

def _extract_delta(chunk):
    """Extrait le morceau de texte d'un evenement SSE, quel que soit le format.
    OpenAI    : choices[0].delta.content
    Anthropic : type=content_block_delta -> delta.text"""
    if not isinstance(chunk, dict):
        return None, None
    if chunk.get("type") == "content_block_delta":
        return (chunk.get("delta") or {}).get("text"), None
    if chunk.get("type") == "error":
        return None, json.dumps(chunk.get("error", {}))[:300]
    ch = (chunk.get("choices") or [None])[0]
    if isinstance(ch, dict):
        piece = (ch.get("delta") or {}).get("content")
        if piece is None:
            piece = (ch.get("message") or {}).get("content")
        return piece, None
    if "error" in chunk:
        return None, json.dumps(chunk["error"])[:300]
    return None, None

@app.route("/api/ai/stream", methods=["POST"])
def call_ai_stream():
    """Relaie le flux du fournisseur vers le navigateur, morceau par morceau."""
    cfg = rd_cfg()
    if needs_key(cfg):
        return jsonify({"error": "Clé API manquante — configurez-la dans Paramètres."}), 400
    d = request.json or {}
    if not d.get("messages"):
        return jsonify({"error": "Aucun message"}), 400

    url     = _chat_url(cfg)
    headers = _headers(cfg)
    body    = {"model": d.get("model") or cfg.get("model"),
               "messages": d["messages"],
               "temperature": d.get("temperature", 0.72),
               "max_tokens": d.get("max_tokens", 3000),
               "stream": True}
    if "anthropic-version" in headers:
        body = _to_anthropic_body(body)
        body["stream"] = True

    def generate():
        try:
            # (connexion, lecture) : 10 min de lecture, un modele local est lent
            r = http.post(url, headers=headers, json=body, stream=True, timeout=(20, 600))
        except Exception as e:
            yield _sse({"error": "Connexion impossible à %s — %s" % (url, str(e)[:200])})
            return
        if r.status_code != 200:
            detail = ""
            try:    detail = r.text[:400]
            except Exception: pass
            yield _sse({"error": "HTTP %d %s" % (r.status_code, detail)})
            return
        got_any = False
        try:
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                line = line.strip()
                if not line.startswith("data:"):
                    continue          # les lignes 'event:' d'Anthropic sont ignorees
                payload = line[5:].strip()
                if payload in ("", "[DONE]"):
                    continue
                try:
                    chunk = json.loads(payload)
                except ValueError:
                    continue
                piece, err = _extract_delta(chunk)
                if err:
                    yield _sse({"error": "API: " + err})
                    return
                if piece:
                    got_any = True
                    yield _sse({"delta": piece})
        except Exception as e:
            yield _sse({"error": "Flux interrompu : %s" % str(e)[:200]})
            return
        if not got_any:
            yield _sse({"error": "Le fournisseur n'a renvoyé aucun contenu."})
            return
        yield _sse({"done": True})

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no",
                             "Connection": "keep-alive"})
# --- ''' + MARKER + ''' ---

''' + OLD_ANCHOR

# ═══════════════════════════════════════════════════════════════════════
#  Client : insere apres le bloc d'accueil
# ═══════════════════════════════════════════════════════════════════════

HTML_ANCHOR = "<!-- ════════ /SB_ONBOARD_PATCH ════════ -->"

CLIENT_BLOCK = HTML_ANCHOR + '''

<!-- ════════ ''' + MARKER + ''' — réponse IA au fil de l'eau ════════ -->
<style>
#aistream{position:fixed;right:18px;bottom:18px;width:360px;max-width:46vw;z-index:400;
  background:var(--bg2);border:1px solid var(--bd);border-radius:8px;padding:10px 12px;
  box-shadow:0 8px 28px rgba(0,0,0,.45);display:none;font-size:12px}
#aistream.on{display:block}
#aistream-hd{display:flex;align-items:center;gap:8px;margin-bottom:6px}
#aistream-ttl{flex:1;font-weight:600;font-size:11px;color:var(--acc)}
#aistream-body{max-height:190px;overflow:auto;white-space:pre-wrap;line-height:1.5;
  color:var(--tx2);font-size:11px}
#aistream-meta{font-size:10px;color:var(--tx2);margin-top:6px;display:flex;
  justify-content:space-between;gap:8px}
</style>

<div id="aistream">
  <div id="aistream-hd">
    <span id="aistream-ttl">✨ L'IA rédige…</span>
    <button class="hbtn" onclick="aiStreamAbort()" title="Interrompre">⏹</button>
  </div>
  <div id="aistream-body"></div>
  <div id="aistream-meta"><span id="aistream-count">0 caractère</span><span id="aistream-time">0 s</span></div>
</div>

<script>
var AISTREAM = {ctrl:null, t0:0, timer:null};

function aiStreamShow(){
  AISTREAM.t0 = Date.now();
  document.getElementById('aistream-body').textContent = '';
  document.getElementById('aistream-count').textContent = '0 caractère';
  document.getElementById('aistream-time').textContent = '0 s';
  document.getElementById('aistream').classList.add('on');
  clearInterval(AISTREAM.timer);
  AISTREAM.timer = setInterval(function(){
    document.getElementById('aistream-time').textContent =
      Math.round((Date.now() - AISTREAM.t0) / 1000) + ' s';
  }, 1000);
}

function aiStreamHide(){
  clearInterval(AISTREAM.timer);
  document.getElementById('aistream').classList.remove('on');
  AISTREAM.ctrl = null;
}

function aiStreamAbort(){
  if(AISTREAM.ctrl) AISTREAM.ctrl.abort();
  aiStreamHide();
}

async function aiStreamCall(data){
  var ctrl = new AbortController();
  AISTREAM.ctrl = ctrl;
  aiStreamShow();

  var resp;
  try {
    resp = await fetch('/api/ai/stream', {
      method : 'POST',
      headers: {'Content-Type': 'application/json'},
      body   : JSON.stringify(data),
      signal : ctrl.signal
    });
  } catch(e){
    aiStreamHide();
    if(e.name === 'AbortError') return {error: 'Interrompu'};
    return null;                       // repli sur la route classique
  }

  if(!resp.ok || !resp.body){
    aiStreamHide();
    if(resp.status === 400){
      try { return await resp.json(); } catch(e){ return {error: 'HTTP 400'}; }
    }
    return null;                       // repli
  }

  var reader  = resp.body.getReader();
  var decoder = new TextDecoder();
  var buf = '', full = '', err = null;
  var bodyEl  = document.getElementById('aistream-body');
  var countEl = document.getElementById('aistream-count');

  try {
    while(true){
      var res = await reader.read();
      if(res.done) break;
      buf += decoder.decode(res.value, {stream:true});
      var lines = buf.split('\\n');
      buf = lines.pop();
      for(var i=0;i<lines.length;i++){
        var line = lines[i].trim();
        if(!line || line.indexOf('data:') !== 0) continue;
        var obj;
        try { obj = JSON.parse(line.slice(5).trim()); } catch(e){ continue; }
        if(obj.error){ err = obj.error; }
        else if(obj.delta){
          full += obj.delta;
          bodyEl.textContent = full.length > 1200 ? '…' + full.slice(-1200) : full;
          bodyEl.scrollTop = bodyEl.scrollHeight;
          countEl.textContent = full.length + ' caractères';
        }
      }
    }
  } catch(e){
    aiStreamHide();
    if(e.name === 'AbortError') return {error: 'Interrompu'};
    return full ? {response: full} : null;
  }

  aiStreamHide();
  if(err)   return {error: err};
  if(!full) return null;               // rien recu : repli
  return {response: full};
}

// Enveloppe post() : seul '/api/ai' est dérouté, tout le reste est intact.
// Tentée tout de suite ET au chargement : ce bloc peut être inséré avant ou
// après la définition de post(), l'enveloppe s'applique dans les deux cas.
function aiStreamWrapPost(){
  if(typeof post !== 'function' || post.__sbStream) return false;
  var _origPost = post;
  var wrapped = async function(url, data){
    if(url !== '/api/ai') return _origPost(url, data);
    var r = await aiStreamCall(data);
    if(r) return r;
    return _origPost(url, data);       // repli silencieux
  };
  wrapped.__sbStream = true;
  post = wrapped;
  return true;
}
if(!aiStreamWrapPost()){
  window.addEventListener('load', aiStreamWrapPost);
}
</script>
<!-- ════════ /''' + MARKER + ''' ════════ -->'''


def patch_python(src):
    n = src.count(OLD_ANCHOR)
    if n != 1:
        return src, [("✗", "Route /api/ai/stream",
                      "ancre introuvable" if n == 0 else "%d occurrences" % n)], True
    return src.replace(OLD_ANCHOR, NEW_ROUTE), \
           [("✓", "Route /api/ai/stream (formats OpenAI + Anthropic)", "1 insertion")], False


def patch_html(src):
    n = src.count(HTML_ANCHOR)
    if n != 1:
        return src, [("✗", "Bloc client de streaming",
                      "ancre introuvable" if n == 0 else "%d occurrences" % n)], True
    return src.replace(HTML_ANCHOR, CLIENT_BLOCK), \
           [("✓", "Panneau live + enveloppe de post()", "1 insertion")], False


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
    if "SB_PROVIDERS_PATCH" not in py_src:
        print("✗ patch_providers.py n'a pas été appliqué. Lancez-le d'abord.")
        return 1
    if MARKER in py_src:
        print("⚠ Déjà appliqué. Rien à faire.")
        return 0

    py_out, py_rep, py_fail = patch_python(py_src)
    html_out, html_rep, html_fail = patch_html(html_src)

    print("\n── second_brain.py " + "─" * 42)
    for m, l, d in py_rep:
        print("  %s %-52s %s" % (m, l, d))
    print("\n── ui.html " + "─" * 50)
    for m, l, d in html_rep:
        print("  %s %-52s %s" % (m, l, d))

    if py_fail or html_fail:
        print("\n✗ ABANDON — rien n'a été écrit.")
        return 2
    if args.dry_run:
        print("\n(--dry-run : aucun fichier modifié)")
        return 0

    shutil.copy2(py_f, py_f.with_suffix(".py.bak5"))
    shutil.copy2(html_f, html_f.with_suffix(".html.bak5"))
    py_f.write_text(py_out, encoding="utf-8")
    html_f.write_text(html_out, encoding="utf-8")
    print("\n✓ Patch appliqué.  Sauvegardes : second_brain.py.bak5, ui.html.bak5")
    print("  Rechargez la page avec Ctrl+Maj+R.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
