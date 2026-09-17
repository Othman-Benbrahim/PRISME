"""Appels IA : reponse simple, flux SSE, synthese de dossier."""
import json
from pathlib import Path

from flask import Blueprint, Response, jsonify, request
import requests as http

from ..config import rd_cfg
from ..vault import _path_err, scoped_dir
from ..providers import (_chat_post, _chat_url, _headers, _to_anthropic_body,
                         needs_key, parse_chat_response)

bp = Blueprint("ai", __name__)

@bp.route("/api/ai", methods=["POST"])
def call_ai():
    cfg = rd_cfg(); key = cfg.get("api_key")
    if needs_key(cfg): return jsonify({"error": "Clé API manquante — configurez-la dans Paramètres."}), 400
    d = request.json
    url = _chat_url(cfg)
    try:
        r = _chat_post(url,
            headers=_headers(cfg),
            json={"model": d.get("model", cfg["model"]), "messages": d["messages"],
                  "temperature": 0.72, "max_tokens": 3000, "stream": False}, timeout=90)
    except http.exceptions.Timeout:
        return jsonify({"error": "Timeout — le serveur n'a pas répondu en 90s"}), 504
    except http.exceptions.ConnectionError as e:
        return jsonify({"error": f"Connexion impossible à {url} — {str(e)[:200]}"}), 503
    except Exception as e:
        return jsonify({"error": f"Erreur réseau : {type(e).__name__}: {str(e)[:200]}"}), 500

    if r.status_code != 200:
        return jsonify({"error": f"HTTP {r.status_code}\n{r.text[:400] or '(vide)'}"}), 500
    if not r.text.strip():
        return jsonify({"error": "Réponse vide du serveur"}), 500

    content, err = parse_chat_response(r.text)
    if err: return jsonify({"error": err}), 500
    return jsonify({"response": content})

def _sse(obj):
    return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"

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

@bp.route("/api/ai/stream", methods=["POST"])
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

@bp.route("/api/ai/folder", methods=["POST"])
def ai_folder():
    cfg = rd_cfg()
    if needs_key(cfg): return jsonify({"error": "Clé API manquante"}), 400
    d = request.json or {}
    try:
        dir_p = scoped_dir(d.get("dir"))
    except (PermissionError, FileNotFoundError) as e:
        return _path_err(e)
    parts, chars = [], 0
    for f in sorted(Path(dir_p).glob("*.md")):
        try:
            txt = f.read_text(encoding="utf-8")
            if chars + len(txt) > 50000: break
            parts.append(f"### {f.name}\n{txt}"); chars += len(txt)
        except: pass
    if not parts: return jsonify({"error": "Aucun .md trouvé"}), 400
    name = Path(dir_p).name
    msgs = [
        {"role": "system", "content": "Tu es un expert en synthèse de connaissances. Analyse ces notes et produis une synthèse structurée en Markdown."},
        {"role": "user",   "content": f"Synthétise le dossier '{name}':\n1. Thèmes principaux\n2. Connexions entre notes\n3. Points clés\n4. Lacunes\n\n---\n" + "\n\n---\n\n".join(parts)}
    ]
    url = _chat_url(cfg)
    try:
        r = _chat_post(url,
            headers=_headers(cfg),
            json={"model": d.get("model", cfg["model"]), "messages": msgs,
                  "temperature": 0.7, "max_tokens": 3000, "stream": False}, timeout=120)
    except http.exceptions.Timeout:
        return jsonify({"error": "Timeout (120s)"}), 504
    except Exception as e:
        return jsonify({"error": f"Erreur réseau : {type(e).__name__}: {str(e)[:200]}"}), 500
    if r.status_code != 200:
        return jsonify({"error": f"HTTP {r.status_code}: {r.text[:400] or '(vide)'}"}), 500
    if not r.text.strip():
        return jsonify({"error": "Réponse vide du serveur"}), 500
    content, err = parse_chat_response(r.text)
    if err: return jsonify({"error": err}), 500
    return jsonify({"response": content})
