#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════╗
║  🧠  SECOND BRAIN  v3  —  Éditeur Markdown + IA         ║
╠══════════════════════════════════════════════════════════╣
║  Installation : pip install flask requests               ║
║  Lancement    : python second_brain.py                   ║
║  Navigateur   : http://localhost:5000                    ║
╚══════════════════════════════════════════════════════════╝
Nouveautés v3 :
  - Explorateur corrigé (FILE_ITEMS, onclick inline)
  - Renommage inline (double-clic)
  - 3 onglets mindmap : Structure / Backlinks / Graphe
  - Graphe force-directed des [[wikilinks]]
  - Recherche full-text (Ctrl+Shift+F)
  - Tags #hashtag dans la sidebar
  - IA sur sélection (barre flottante)
  - IA synthèse de dossier
  - Suggestions de [[liens]]
  - Wikilinks cliquables en aperçu
"""

import json, uuid, re, threading, webbrowser, shutil, time, sys, os
from pathlib import Path
from flask import Flask, request, jsonify, Response
import requests as http

app = Flask(__name__)

DATA  = Path.home() / ".secondbrain"
DATA.mkdir(exist_ok=True)
CFG_F = DATA / "config.json"

DEFAULT_VAULT = Path.home() / "Documents" / "Second Brain"

DEF_CFG = {
    "api_key"   : "",
    "model"     : "",
    "base_url"  : "",
    "workspace" : str(DEFAULT_VAULT),
    "configured": False,
}

# ── Config ─────────────────────────────────────────────────────────────────────

def rd_cfg():
    if CFG_F.exists():
        try: return {**DEF_CFG, **json.loads(CFG_F.read_text())}
        except: pass
    return {**DEF_CFG}

def wr_cfg(data):
    c = rd_cfg(); c.update(data)
    CFG_F.write_text(json.dumps(c, indent=2, ensure_ascii=False))


# --- SB_ONBOARD_PATCH ---
WELCOME = """# Bienvenue dans Second Brain

Ceci est votre première note. Tout ce que vous écrivez ici vit dans un
simple fichier `.md` sur votre disque — aucun cloud, aucune base de données.

## Pour commencer

- `Ctrl+S` enregistre la note en cours
- `Ctrl+Shift+F` cherche dans toutes vos notes
- Écrivez [[une-autre-note]] pour créer un lien — il devient cliquable

Bonne écriture.
"""

def ensure_vault(path):
    """Cree le dossier de notes s'il n'existe pas, avec une note d'accueil."""
    p = Path(path).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    if not any(p.glob("*.md")):
        (p / "Bienvenue.md").write_text(WELCOME, encoding="utf-8")
    return p

def _is_local(url):
    return any(h in (url or "") for h in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]"))

# --- SB_PROVIDERS_PATCH ---
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
    return http.post(url, headers=headers, json=body, timeout=timeout, **kw)
# --- SB_PROVIDERS_PATCH ---

def needs_key(cfg):
    """True si une cle est indispensable : service distant sans cle configuree."""
    return not cfg.get("api_key") and not _is_local(cfg.get("base_url", ""))

SKIP_DIRS = {"node_modules", "AppData", "Library", ".git", ".trash",
             "__pycache__", "venv", ".venv", "Windows", "Program Files",
             "Program Files (x86)", "$RECYCLE.BIN", "OneDriveTemp"}
# --- SB_VAULT_PATCH ---
def vault_root():
    """Racine autorisee pour toute operation de fichier."""
    return Path(rd_cfg().get("workspace") or Path.home()).expanduser().resolve()

def safe_path(raw, must_exist=False):
    """Resout un chemin et REFUSE tout ce qui sort du vault.
    Un chemin relatif est interprete depuis la racine du vault.
    Leve PermissionError (hors vault) ou FileNotFoundError."""
    root = vault_root()
    p = Path(str(raw or "").strip()).expanduser()
    if not p.is_absolute():
        p = root / p
    try:
        p = p.resolve()
    except OSError:
        raise PermissionError("Chemin invalide")
    if p != root and root not in p.parents:
        raise PermissionError(
            "Hors de l'espace de travail (%s). Pour utiliser ce dossier, "
            "définissez-le comme espace de travail." % root)
    return p

def in_trash(p):
    return ".trash" in Path(p).parts

def to_trash(p):
    """Deplace vers <vault>/.trash/AAAA-MM-JJ/ au lieu de supprimer.
    Rien n'est jamais perdu par un simple clic — le menage se fait a la main."""
    trash = vault_root() / ".trash" / time.strftime("%Y-%m-%d")
    trash.mkdir(parents=True, exist_ok=True)
    target = trash / p.name
    i = 1
    while target.exists():
        target = trash / ("%s_%d%s" % (p.stem, i, p.suffix))
        i += 1
    shutil.move(str(p), str(target))
    return target

def _path_err(e):
    """Traduit une exception de chemin en reponse JSON."""
    if isinstance(e, PermissionError):
        return jsonify({"error": str(e)}), 403
    if isinstance(e, FileNotFoundError):
        return jsonify({"error": "Fichier ou dossier introuvable"}), 404
    return jsonify({"error": str(e)}), 500
# --- SB_VAULT_PATCH ---

# --- SB_HARDENING_PATCH ---
# ── Jeton d'acces local ────────────────────────────────────────────────
SB_TOKEN   = uuid.uuid4().hex
SB_NO_AUTH = os.getenv("SECONDBRAIN_NO_AUTH") == "1"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", ""}

@app.route("/api/token", methods=["GET"])
def api_token():
    """Le navigateur recupere le jeton au chargement. Une page tierce peut
    declencher cet appel mais ne peut PAS en lire la reponse : la politique
    CORS l'en empeche, aucun en-tete Access-Control-Allow-Origin n'est emis."""
    return jsonify({"token": SB_TOKEN})

@app.before_request
def _sb_guard():
    # Verrou 1 : l'en-tete Host doit designer la machine locale.
    # C'est ce qui bloque le DNS rebinding — le navigateur y envoie le
    # domaine de l'attaquant, pas 127.0.0.1.
    host = (request.host or "").rsplit(":", 1)[0].strip("[]").lower()
    if host not in LOCAL_HOSTS:
        return jsonify({"error": "Hôte non autorisé : %s" % host}), 403
    if SB_NO_AUTH:
        return None
    # Verrou 2 : jeton obligatoire sur /api/, sauf pour le recuperer.
    p = request.path or ""
    if p.startswith("/api/") and p != "/api/token":
        if request.headers.get("X-SB-Token") != SB_TOKEN:
            return jsonify({"error": "Jeton absent ou invalide — rechargez la page "
                                     "(Ctrl+Maj+R)."}), 403
    return None

# ── Index de recherche ─────────────────────────────────────────────────
_IDX      = {}                  # racine -> {chemin: {mtime, text, lower, tags}}
_IDX_LOCK = threading.Lock()

def index_refresh(root):
    """Met l'index a jour et le retourne. Ne relit que les fichiers dont la
    date de modification a change — un stat() au lieu d'une lecture complete."""
    root = str(root)
    with _IDX_LOCK:
        store = _IDX.setdefault(root, {})
        seen = set()
        for f in iter_md(root):
            sp = str(f)
            seen.add(sp)
            try:
                mt = f.stat().st_mtime
            except OSError:
                continue
            e = store.get(sp)
            if e is not None and e["mtime"] == mt:
                continue
            try:
                txt = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            store[sp] = {"mtime": mt, "text": txt, "lower": txt.lower(),
                         "tags": extract_tags(txt)}
        for gone in set(store) - seen:
            store.pop(gone, None)
        return dict(store)

# ── Instantane avant ecrasement ────────────────────────────────────────
SNAPSHOT_INTERVAL = 300         # 5 min : une sauvegarde par Ctrl+S ne spamme pas
_LAST_SNAP = {}

def snapshot(p):
    """Copie la version actuelle dans .trash/versions/ avant de l'ecraser.
    Limite a une copie toutes les SNAPSHOT_INTERVAL secondes par fichier."""
    try:
        if not p.exists() or p.is_dir() or in_trash(p):
            return None
        now  = time.time()
        last = _LAST_SNAP.get(str(p), 0)
        if now - last < SNAPSHOT_INTERVAL:
            return None
        d = vault_root() / ".trash" / "versions" / time.strftime("%Y-%m-%d")
        d.mkdir(parents=True, exist_ok=True)
        dest = d / ("%s_%s%s" % (p.stem, time.strftime("%H%M%S"), p.suffix))
        shutil.copy2(str(p), str(dest))
        _LAST_SNAP[str(p)] = now
        return dest
    except Exception:
        return None               # un instantane raté ne doit jamais bloquer une sauvegarde
# --- SB_HARDENING_PATCH ---

MAX_SCAN = 5000

def iter_md(root):
    """Parcourt les .md en evitant les dossiers systeme et en plafonnant le total.
    Remplace rglob('*.md') : sur un dossier utilisateur entier, rglob gelait
    l'application pendant une minute au premier lancement."""
    root = Path(root)
    if not root.exists():
        return
    n = 0
    for p in root.rglob("*.md"):
        try:
            parts = p.relative_to(root).parts[:-1]
        except ValueError:
            continue
        if any(part in SKIP_DIRS or part.startswith(".") for part in parts):
            continue
        n += 1
        if n > MAX_SCAN:
            return
        yield p
# --- SB_ONBOARD_PATCH ---

# ── Variables d'environnement (.env) ────────────────────────────────────────────

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

# .env racine du projet, charge au demarrage (avant tout plugin)
load_env_file(Path(__file__).parent / ".env")

# ── Markdown helpers ────────────────────────────────────────────────────────────

def _id(): return str(uuid.uuid4())[:8]
def _node(t, c="", ch=None):
    return {"id": _id(), "title": t, "content": c, "children": ch or [], "collapsed": False}

def extract_wikilinks(content):
    """Compatibilité — délègue à extract_link_refs."""
    return list(extract_link_refs(content))

# Patterns de liens reconnus dans un .md
_RE_WIKI    = re.compile(r"\[\[([^\]|#\n]+?)(?:[|#][^\]\n]*?)?\]\]")
_RE_MDLINK  = re.compile(r"\[[^\]\n]*\]\(\s*([^)\s#?]+?\.md)(?:[#?][^)]*)?\s*\)")
_RE_QUOTED  = re.compile(r"""['"`]([^'"`\n]+?\.md)['"`]""")
_RE_BARE    = re.compile(r"(?:^|[\s,;>(])((?:\.{1,2}/)?[A-Za-z0-9_][A-Za-z0-9_\-./]*\.md)(?=[\s,;:.)]|$)", re.MULTILINE)

def extract_link_refs(content):
    """
    Renvoie l'ensemble des références à d'autres .md trouvées dans le contenu.
    4 patterns reconnus :
      1. [[wikilink]]               (avec |alias et #ancre facultatifs)
      2. [label](path/to/file.md)   (lien Markdown standard)
      3. 'foo.md' "foo.md" `foo.md` (chemins entre guillemets/backticks)
      4. references/file.md         (chemin nu en texte courant)
    """
    refs = set()
    for m in _RE_WIKI.finditer(content):   refs.add(m.group(1).strip())
    for m in _RE_MDLINK.finditer(content):
        v = m.group(1).strip()
        if not v.lower().startswith(("http://","https://")): refs.add(v)
    for m in _RE_QUOTED.finditer(content):
        v = m.group(1).strip()
        if not v.lower().startswith(("http://","https://")): refs.add(v)
    # La regex bare exclut nativement les URLs (contexte préc. interdit / et :)
    for m in _RE_BARE.finditer(content): refs.add(m.group(1).strip())
    return refs

def resolve_ref(raw_ref, source_path, vault_paths):
    """
    Résout une référence brute en chemin réel du vault, ou None.
    Cascade :
      1. Chemin relatif au dossier du fichier source (ex: ../parent/foo.md)
      2. Chemin partiel matchant un suffixe d'un fichier du vault (ex: references/foo.md)
      3. Fuzzy match par nom de fichier (ex: foo → foo.md n'importe où)
    """
    if not raw_ref: return None
    ref = raw_ref.strip().lstrip("/")
    if not ref.lower().endswith(".md"): ref = ref + ".md"
    ref_norm = ref.replace("\\", "/")

    # 1. Relatif au dossier source
    if source_path:
        try:
            cand = (Path(source_path).parent / ref).resolve()
            cand_s = str(cand)
            if cand_s in vault_paths: return cand_s
        except Exception: pass

    # 2. Suffixe (ex: 'references/foo.md' matche '...\skills\X\references\foo.md')
    for vp in vault_paths:
        if vp.replace("\\", "/").lower().endswith("/" + ref_norm.lower()):
            return vp
        if vp.replace("\\", "/").lower().endswith(ref_norm.lower()):
            return vp

    # 3. Fuzzy par nom de fichier
    stem = Path(ref).stem.lower()
    for vp in vault_paths:
        if Path(vp).stem.lower() == stem: return vp
    return None

def extract_tags(content):
    return list({t for t in re.findall(r"(?<!\w)#([a-zA-Z0-9_\-]+)", content)})

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

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index(): return Response(PAGE, mimetype="text/html")

@app.route("/api/plugins", methods=["GET"])
def list_plugins():
    """Liste les plugins chargés (pour debug et future UI de gestion)."""
    return jsonify({
        "count": len(LOADED_PLUGINS),
        "plugins": [{
            "name": p["name"],
            "dir": p["dir"],
            "description": p["manifest"].get("description", ""),
            "version": p["manifest"].get("version", "?"),
            "buttons": p["manifest"].get("buttons", []),
        } for p in LOADED_PLUGINS]
    })

# --- SB_ONBOARD_PATCH ---
@app.route("/api/setup/state", methods=["GET"])
def setup_state():
    c = rd_cfg()
    return jsonify({
        "configured": bool(c.get("configured")),
        "suggested_workspace": str(DEFAULT_VAULT),
        "workspace": c.get("workspace", ""),
    })

@app.route("/api/setup", methods=["POST"])
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
# --- SB_ONBOARD_PATCH ---

@app.route("/api/config", methods=["GET"])
def get_cfg():
    c = rd_cfg()
    return jsonify({**c, "api_key": "●●●" if c.get("api_key") else "", "has_key": bool(c.get("api_key"))})

@app.route("/api/config", methods=["POST"])
def set_cfg(): wr_cfg(request.json); return jsonify({"ok": True})

@app.route("/api/ai", methods=["POST"])
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

# --- SB_STREAM_PATCH ---
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
# --- SB_STREAM_PATCH ---

@app.route("/api/files", methods=["GET"])
def list_files():
    raw = request.args.get("path", "").strip() or rd_cfg().get("workspace", str(Path.home()))
    p = Path(raw)
    try:
        items = sorted(
            [{"name": i.name, "path": str(i), "is_dir": i.is_dir(),
              "is_md": i.suffix.lower() in (".md", ".txt", ".markdown")}
             for i in p.iterdir() if not i.name.startswith(".")],
            key=lambda x: (not x["is_dir"], x["name"].lower())
        )
        return jsonify({"path": str(p), "parent": str(p.parent), "items": items})
    except PermissionError: return jsonify({"error": "Accès refusé"}), 403
    except FileNotFoundError: return jsonify({"error": "Dossier introuvable"}), 404

@app.route("/api/files/read", methods=["GET"])
def read_file():
    try:
        p = safe_path(request.args.get("path", ""))
        # errors="replace" : une note en CP-1252 ne doit pas faire echouer la lecture
        return jsonify({"content": p.read_text(encoding="utf-8", errors="replace")})
    except (PermissionError, FileNotFoundError) as e: return _path_err(e)
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/files/save", methods=["POST"])
def save_file():
    d = request.json or {}
    try:
        p = safe_path(d.get("path", ""))
        p.parent.mkdir(parents=True, exist_ok=True)
        snap = snapshot(p)                      # version precedente -> .trash/versions/
        p.write_text(d.get("content", ""), encoding="utf-8")
        return jsonify({"ok": True, "snapshot": str(snap) if snap else None})
    except (PermissionError, FileNotFoundError) as e: return _path_err(e)
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/files/new", methods=["POST"])
def new_file():
    d = request.json or {}
    name = (d.get("name") or "nouveau.md").strip()
    if any(c in name for c in '\\/:*?"<>|'):
        return jsonify({"error": "Nom de fichier invalide"}), 400
    if not name.endswith(".md"): name += ".md"
    try:
        dir_p = safe_path(d.get("dir") or rd_cfg().get("workspace", ""))
        path  = safe_path(dir_p / name)
    except (PermissionError, FileNotFoundError) as e: return _path_err(e)
    if path.exists(): return jsonify({"error": "Fichier existant"}), 409
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {name.replace('.md','')}\n\n", encoding="utf-8")
        return jsonify({"ok": True, "path": str(path)})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/files/rename", methods=["POST"])
def rename_file():
    d = request.json
    try:
        old = safe_path(d.get("old", ""))
    except (PermissionError, FileNotFoundError) as e: return _path_err(e)
    new_name = (d.get("new_name") or "").strip()
    if not old.exists() or not new_name: return jsonify({"error": "Paramètres invalides"}), 400
    if any(c in new_name for c in '\\/:*?"<>|'):
        return jsonify({"error": "Nom de fichier invalide"}), 400
    new_path = old.parent / new_name
    try: old.rename(new_path); return jsonify({"ok": True, "new_path": str(new_path)})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/files/delete", methods=["POST"])
def delete_file():
    """Ne supprime plus : deplace vers <vault>/.trash/AAAA-MM-JJ/.
    Seul un element deja dans la corbeille est reellement efface."""
    try:
        p = safe_path((request.json or {}).get("path", ""))
    except (PermissionError, FileNotFoundError) as e: return _path_err(e)
    if p == vault_root():
        return jsonify({"error": "Impossible de supprimer la racine de l'espace de travail"}), 400
    if not p.exists():
        return jsonify({"error": "Fichier ou dossier introuvable"}), 404
    try:
        if in_trash(p):                      # deja dans la corbeille : suppression definitive
            if p.is_dir(): shutil.rmtree(p)
            else: p.unlink()
            return jsonify({"ok": True, "trashed": False})
        dest = to_trash(p)
        return jsonify({"ok": True, "trashed": True, "trash_path": str(dest)})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/search", methods=["GET"])
def search_files():
    query = request.args.get("q", "").strip()
    dir_p = request.args.get("dir", "").strip() or rd_cfg().get("workspace", str(Path.home()))
    if len(query) < 2: return jsonify({"results": []})
    results, total = [], 0
    ql = query.lower()
    idx = index_refresh(dir_p)
    for sp in sorted(idx):
        entry = idx[sp]
        if ql not in entry["lower"]: continue
        f = Path(sp)
        matches = []
        for i, line in enumerate(entry["text"].split("\n")):
            if ql in line.lower():
                matches.append({"line": i+1, "text": line[:140].strip()})
                if len(matches) >= 4: break
        try:    rel = str(f.relative_to(Path(dir_p)))
        except Exception: rel = f.name
        results.append({"path": sp, "name": f.name, "rel": rel, "matches": matches})
        total += 1
        if total >= 40: break
    return jsonify({"results": results})

@app.route("/api/tags", methods=["GET"])
def get_tags():
    dir_p = request.args.get("dir", "").strip() or rd_cfg().get("workspace", str(Path.home()))
    tags = {}
    idx = index_refresh(dir_p)
    for sp in sorted(idx):
        for tag in idx[sp]["tags"]:
            tags.setdefault(tag, []).append(sp)
    return jsonify({"tags": [{"tag": k, "count": len(v), "files": v}
                              for k, v in sorted(tags.items(), key=lambda x: -len(x[1]))]})

@app.route("/api/files/graph", methods=["GET"])
def files_graph():
    dir_p = request.args.get("dir", "").strip() or rd_cfg().get("workspace", str(Path.home()))
    files = sorted(iter_md(dir_p))
    vault_paths = {str(f) for f in files}
    degree = {str(f): 0 for f in files}
    edges, seen = [], set()
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
            for ref in extract_link_refs(content):
                target = resolve_ref(ref, str(f), vault_paths)
                if target and target != str(f):
                    key = tuple(sorted([str(f), target]))
                    if key not in seen:
                        seen.add(key); edges.append({"source": str(f), "target": target})
                    degree[str(f)]   = degree.get(str(f),   0) + 1
                    degree[target]   = degree.get(target,   0) + 1
        except: pass
    nodes = [{"id": str(f), "name": f.stem, "path": str(f),
              "degree": degree.get(str(f), 0),
              "rel": str(f.relative_to(dir_p)) if str(f).startswith(dir_p) else f.name}
             for f in files]
    return jsonify({"nodes": nodes, "links": edges})

@app.route("/api/files/backlinks", methods=["GET"])
def backlinks():
    file_path = request.args.get("path", "")
    dir_p     = request.args.get("dir", "").strip() or rd_cfg().get("workspace", str(Path.home()))
    if not file_path: return jsonify({"backlinks": []})
    try:
        target_resolved = str(Path(file_path).resolve())
    except Exception:
        target_resolved = file_path

    vault_paths = {str(f) for f in iter_md(dir_p)}
    results = []
    for f in sorted(iter_md(dir_p)):
        if str(f) == file_path: continue
        try:
            content = f.read_text(encoding="utf-8")
            refs = extract_link_refs(content)
            matched = None
            for ref in refs:
                resolved = resolve_ref(ref, str(f), vault_paths)
                if not resolved: continue
                try: resolved_norm = str(Path(resolved).resolve())
                except: resolved_norm = resolved
                if resolved_norm == target_resolved:
                    matched = ref; break
            if matched:
                # Cherche une ligne contenant la référence pour le contexte
                ctx = ""
                ml = matched.lower()
                for l in content.split("\n"):
                    if ml in l.lower():
                        ctx = l.strip()[:150]; break
                results.append({"path": str(f), "name": f.name, "ctx": ctx, "ref": matched})
        except: pass
    return jsonify({"backlinks": results})

@app.route("/api/ai/folder", methods=["POST"])
def ai_folder():
    cfg = rd_cfg(); key = cfg.get("api_key")
    if not key: return jsonify({"error": "Clé API manquante"}), 400
    d = request.json; dir_p = d.get("dir", "")
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

@app.route("/api/files/find", methods=["GET"])
def find_file():
    """Trouve un .md à partir d'une référence brute, avec résolution intelligente."""
    ref      = request.args.get("name", "").strip()
    src      = request.args.get("from", "").strip()
    dir_p    = request.args.get("dir", "").strip() or rd_cfg().get("workspace", str(Path.home()))
    if not ref: return jsonify({"error": "Référence vide"}), 400
    try:
        vault_paths = {str(f) for f in iter_md(dir_p)}
        # 1. Si source connue, résoudre depuis là
        if src:
            resolved = resolve_ref(ref, src, vault_paths)
            if resolved:
                return jsonify({"path": resolved, "content": Path(resolved).read_text(encoding="utf-8")})
        # 2. Sinon, tenter une résolution sans contexte source
        resolved = resolve_ref(ref, "", vault_paths)
        if resolved:
            return jsonify({"path": resolved, "content": Path(resolved).read_text(encoding="utf-8")})
        return jsonify({"error": "Fichier introuvable : " + ref}), 404
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/test", methods=["GET"])
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

@app.route("/api/models", methods=["GET"])
def get_models():
    cfg = rd_cfg()
    if needs_key(cfg): return jsonify({"models": []})
    if not cfg.get("base_url"): return jsonify({"models": []})
    try:
        r = http.get(cfg["base_url"].rstrip("/")+"/models",
            headers=_headers(cfg), timeout=10)
        return jsonify({"models": [m["id"] for m in r.json().get("data", [])]})
    except: return jsonify({"models": []})

# ── HTML (embarqué) ────────────────────────────────────────────────────────────

if getattr(sys, "frozen", False):
    BASE = Path(sys._MEIPASS)            # fichiers embarqués DANS l'exe
    HOME = Path(sys.executable).parent   # dossier où se trouve l'exe
else:
    BASE = HOME = Path(__file__).parent

with open(BASE / "ui.html", encoding="utf-8") as _f:
    PAGE_TEMPLATE = _f.read()
# ══════════════════════════════════════════════════
#  PLUGIN LOADER
# ══════════════════════════════════════════════════

PLUGINS_DIR = HOME / "plugins"
LOADED_PLUGINS = []   # liste de dicts avec name, manifest, ui_css, ui_js, ui_html

def load_plugins(flask_app, cfg_reader):
    """
    Découvre et charge tous les plugins du dossier plugins/.
    Chaque sous-dossier avec manifest.json est un plugin.
    """
    import importlib.util
    if not PLUGINS_DIR.exists(): return
    for pdir in sorted(PLUGINS_DIR.iterdir()):
        if not pdir.is_dir() or pdir.name.startswith(("_", ".")): continue
        manifest_p = pdir / "manifest.json"
        if not manifest_p.exists():
            print(f"  ⚠ Plugin '{pdir.name}' : pas de manifest.json — ignoré")
            continue
        try:
            manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ✗ Plugin '{pdir.name}' : manifest invalide ({e})")
            continue

        # .env propre au plugin (cles API, etc.) -> os.environ
        load_env_file(pdir / ".env")
        for _k in manifest.get("env", []):
            if not os.getenv(_k):
                print(f"  ⚠ Plugin '{pdir.name}' : variable manquante : {_k}")

        # Charger le module Python (s'il existe) et appeler register()
        init_p = pdir / "__init__.py"
        if init_p.exists():
            try:
                spec = importlib.util.spec_from_file_location(f"plugins.{pdir.name}", init_p)
                mod  = importlib.util.module_from_spec(spec)
                # Le plugin va importer 'from second_brain import ...' — s'assurer que ce nom est résolvable
                sys.modules.setdefault("second_brain", sys.modules[__name__])
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    mod.register(flask_app, cfg_reader)
            except Exception as e:
                import traceback; traceback.print_exc()
                print(f"  ✗ Plugin '{pdir.name}' : erreur Python ({e}) — UI désactivée")
                continue

        # Lire les fichiers UI
        def _read(rel):
            p = pdir / rel
            return p.read_text(encoding="utf-8") if p.exists() else ""

        LOADED_PLUGINS.append({
            "name"    : manifest.get("name", pdir.name),
            "dir"     : pdir.name,
            "manifest": manifest,
            "ui_css"  : _read("ui.css"),
            "ui_js"   : _read("ui.js"),
            "ui_html" : _read("ui.html"),
        })
        print(f"  ✓ Plugin chargé : {pdir.name} ({manifest.get('name', '?')})")

def assemble_page():
    """Injecte le contenu des plugins dans le template PAGE."""
    css   = "\n".join(f"/* === plugin: {p['name']} === */\n{p['ui_css']}" for p in LOADED_PLUGINS if p['ui_css'])
    html  = "\n".join(f"<!-- === plugin: {p['name']} === -->\n{p['ui_html']}" for p in LOADED_PLUGINS if p['ui_html'])
    js    = "\n".join(f"// === plugin: {p['name']} ===\n{p['ui_js']}" for p in LOADED_PLUGINS if p['ui_js'])
    btns = []
    for p in LOADED_PLUGINS:
        for b in p["manifest"].get("buttons", []):
            if b.get("panel") == "toolbar":
                btns.append(
                    f'<button class="hbtn" onclick="{b.get("onclick","")}" '
                    f'title="{b.get("title","")}">{b.get("label","")}</button>'
                )
    toolbar_btns = "\n      ".join(btns)
    page = PAGE_TEMPLATE
    page = page.replace("/* PLUGIN_CSS */",                css)
    page = page.replace("<!-- PLUGIN_HTML -->",            html)
    page = page.replace("/* PLUGIN_JS */",                 js)
    page = page.replace("<!-- PLUGIN_TOOLBAR_BUTTONS -->", toolbar_btns)
    return page

# PAGE sera assemblée après le chargement des plugins (dans le main)
PAGE = PAGE_TEMPLATE

# ── Lancement ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("""
  ╔══════════════════════════════════════════╗
  ║   🧠  Second Brain  v3  —  démarrage    ║
  ╠══════════════════════════════════════════╣
  ║   Navigateur : http://localhost:5000     ║
  ║   Ctrl+C pour arrêter                   ║
  ╚══════════════════════════════════════════╝
""")
    print("→ Chargement des plugins…")
    load_plugins(app, rd_cfg)
    PAGE = assemble_page()
    print(f"→ {len(LOADED_PLUGINS)} plugin(s) actif(s)\n")
    threading.Timer(1.6, lambda: webbrowser.open("http://localhost:5000")).start()
    app.run(port=5000, debug=False)
