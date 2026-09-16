#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_onboarding.py — applique les modifications "premier lancement" + "cle API
facultative" a second_brain.py et ui.html.

  python patch_onboarding.py --dry-run    # montre ce qui serait fait, n'ecrit rien
  python patch_onboarding.py              # applique, apres sauvegarde .bak

Le script est SUR :
  - il refuse d'ecrire si une seule ancre est introuvable (tout ou rien) ;
  - il sauvegarde second_brain.py.bak et ui.html.bak avant toute ecriture ;
  - relance sans effet s'il a deja ete applique (idempotent).

Pour revenir en arriere : renommer les .bak par-dessus les originaux.
"""
import argparse
import shutil
import sys
from pathlib import Path

MARKER = "# --- SB_ONBOARD_PATCH ---"

# ═══════════════════════════════════════════════════════════════════════
#  Blocs injectes
# ═══════════════════════════════════════════════════════════════════════

NEW_DEF_CFG = '''DEFAULT_VAULT = Path.home() / "Documents" / "Second Brain"

DEF_CFG = {
    "api_key"   : "",
    "model"     : "",
    "base_url"  : "",
    "workspace" : str(DEFAULT_VAULT),
    "configured": False,
}'''

OLD_DEF_CFG = '''DEF_CFG = {
    "api_key"  : "",
    "model"    : "gpt-4o",
    "base_url" : "https://fantasyai.cloud/api/v1",
    "workspace": str(Path.home()),
}'''

OLD_WR_CFG = '''def wr_cfg(data):
    c = rd_cfg(); c.update(data)
    CFG_F.write_text(json.dumps(c, indent=2, ensure_ascii=False))'''

HELPERS = OLD_WR_CFG + '''


''' + MARKER + '''
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

def _headers(cfg):
    """Authorization uniquement si une cle existe — Ollama et LM Studio n'en veulent pas."""
    h = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        h["Authorization"] = "Bearer " + cfg["api_key"]
    return h

def needs_key(cfg):
    """True si une cle est indispensable : service distant sans cle configuree."""
    return not cfg.get("api_key") and not _is_local(cfg.get("base_url", ""))

SKIP_DIRS = {"node_modules", "AppData", "Library", ".git", ".trash",
             "__pycache__", "venv", ".venv", "Windows", "Program Files",
             "Program Files (x86)", "$RECYCLE.BIN", "OneDriveTemp"}
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
''' + MARKER

SETUP_ROUTES = MARKER + '''
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
''' + MARKER + '''

@app.route("/api/config", methods=["GET"])'''


# ═══════════════════════════════════════════════════════════════════════
#  Remplacements dans second_brain.py
#  (ancre, remplacement, nombre attendu, libelle)
# ═══════════════════════════════════════════════════════════════════════

PY_EDITS = [
    (OLD_DEF_CFG, NEW_DEF_CFG, 1,
     "Config par defaut (vault Documents/Second Brain, provider vierge)"),

    (OLD_WR_CFG, HELPERS, 1,
     "Helpers : ensure_vault, _headers, needs_key, iter_md"),

    ('@app.route("/api/config", methods=["GET"])', SETUP_ROUTES, 1,
     "Routes /api/setup et /api/setup/state"),

    # ── Cle facultative : les quatre gardes ──────────────────────────
    ('    key = cfg.get("api_key")\n    if not key: return None, "Clé API manquante"',
     '    key = cfg.get("api_key")\n    if needs_key(cfg): return None, "Clé API manquante"',
     1, "_ai_call : cle facultative en local"),

    ('    cfg = rd_cfg(); key = cfg.get("api_key")\n'
     '    if not key: return jsonify({"error": "Clé API manquante — configurez-la dans Paramètres."}), 400',
     '    cfg = rd_cfg(); key = cfg.get("api_key")\n'
     '    if needs_key(cfg): return jsonify({"error": "Clé API manquante — configurez-la dans Paramètres."}), 400',
     1, "/api/ai : cle facultative en local"),

    ('    cfg = rd_cfg(); key = cfg.get("api_key")\n'
     '    if not key: return jsonify({"ok": False, "step": "config", "error": "Pas de clé API"})',
     '    cfg = rd_cfg(); key = cfg.get("api_key")\n'
     '    if needs_key(cfg): return jsonify({"ok": False, "step": "config", "error": "Pas de clé API"})',
     1, "/api/test : cle facultative en local"),

    ('    if not cfg.get("api_key"): return jsonify({"models": []})\n'
     '    try:\n'
     '        r = http.get(cfg["base_url"]+"/models",\n'
     '            headers={"Authorization": f"Bearer {cfg[\'api_key\']}"}, timeout=10)',
     '    if needs_key(cfg): return jsonify({"models": []})\n'
     '    if not cfg.get("base_url"): return jsonify({"models": []})\n'
     '    try:\n'
     '        r = http.get(cfg["base_url"].rstrip("/")+"/models",\n'
     '            headers=_headers(cfg), timeout=10)',
     1, "/api/models : cle facultative + URL normalisee"),

    # ── En-tetes HTTP centralises (4 occurrences) ────────────────────
    ('headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},',
     'headers=_headers(cfg),',
     4, "En-tetes HTTP via _headers(cfg)"),

    # ── Parcours du vault (3 occurrences) ────────────────────────────
    ('Path(dir_p).rglob("*.md")', 'iter_md(dir_p)', 3,
     "Parcours des notes via iter_md (evite le gel au demarrage)"),
]

# Le nombre d'occurrences de certaines ancres peut varier selon ta version :
# ces deux-la sont tolerantes (au moins 1, au plus N).
FLEXIBLE = {
    'headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},',
    'Path(dir_p).rglob("*.md")',
}


# ═══════════════════════════════════════════════════════════════════════
#  Bloc ui.html
# ═══════════════════════════════════════════════════════════════════════

ONBOARDING_HTML = '''
<!-- ════════ SB_ONBOARD_PATCH — Premier lancement ════════ -->
<div id="monb" class="ov"><div class="mb" style="width:520px;max-width:94vw">
  <div class="mt">🧠 Bienvenue dans Second Brain</div>
  <div class="minfo">Deux réglages et c'est parti. Tout est modifiable plus tard dans ⚙ Paramètres.</div>

  <div><label>1. Où ranger vos notes</label>
    <input id="onb-ws" type="text">
    <div style="font-size:11px;color:var(--tx2);margin-top:4px">
      Le dossier sera créé s'il n'existe pas, avec une note d'accueil.
    </div>
  </div>

  <div><label>2. Quelle IA</label>
    <select id="onb-prov" onchange="onbProv()"></select>
    <div id="onb-help" style="font-size:11px;color:var(--tx2);margin-top:4px"></div>
  </div>

  <div id="onb-key-block"><label>Clé API</label>
    <input id="onb-key" type="password" placeholder="">
  </div>

  <div><label>URL du service</label><input id="onb-url" type="text"></div>
  <div><label>Modèle</label><input id="onb-model" type="text" list="onb-models">
    <datalist id="onb-models"></datalist>
  </div>

  <div id="onb-status" style="font-size:11px;margin-top:8px;min-height:14px"></div>

  <div class="mf">
    <button class="btn bs" style="width:auto;padding:7px 16px" onclick="onbTest()">🔌 Tester</button>
    <button class="btn bp" style="width:auto;padding:7px 16px" onclick="onbSave()">Commencer →</button>
  </div>
</div></div>

<script>
var ONB_PROVIDERS = [
  {id:'openrouter', label:'OpenRouter (accès à tous les modèles)', url:'https://openrouter.ai/api/v1',
   model:'openai/gpt-4o-mini', key:true, ph:'sk-or-v1-…',
   help:'Une seule clé pour GPT, Claude, Gemini, Llama. Créez-la sur openrouter.ai.'},
  {id:'openai', label:'OpenAI', url:'https://api.openai.com/v1',
   model:'gpt-4o-mini', key:true, ph:'sk-…', help:'Clé depuis platform.openai.com.'},
  {id:'fantasy', label:'FantasyAI', url:'https://fantasyai.cloud/api/v1',
   model:'gpt-4o', key:true, ph:'fantasy-…', help:''},
  {id:'ollama', label:'Ollama (local, gratuit)', url:'http://localhost:11434/v1',
   model:'llama3.1', key:false, ph:'',
   help:'Aucune clé. Ollama doit tourner sur votre machine (ollama serve).'},
  {id:'lmstudio', label:'LM Studio (local, gratuit)', url:'http://localhost:1234/v1',
   model:'', key:false, ph:'',
   help:'Aucune clé. Démarrez le serveur local dans LM Studio.'},
  {id:'custom', label:'Autre (compatible OpenAI)', url:'', model:'', key:true, ph:'',
   help:'Tout service exposant /chat/completions au format OpenAI.'}
];

function onbCur(){
  var v = document.getElementById('onb-prov').value;
  for(var i=0;i<ONB_PROVIDERS.length;i++){ if(ONB_PROVIDERS[i].id===v) return ONB_PROVIDERS[i]; }
  return ONB_PROVIDERS[0];
}

function onbProv(){
  var p = onbCur();
  document.getElementById('onb-url').value = p.url;
  document.getElementById('onb-model').value = p.model;
  document.getElementById('onb-key').placeholder = p.ph;
  document.getElementById('onb-help').textContent = p.help;
  document.getElementById('onb-key-block').style.display = p.key ? 'block' : 'none';
  if(!p.key) document.getElementById('onb-key').value = '';
}

async function onbTest(){
  var st = document.getElementById('onb-status');
  st.style.color = 'var(--tx2)';
  st.textContent = '⏳ Test en cours…';
  await post('/api/config', {
    base_url: document.getElementById('onb-url').value.trim(),
    api_key:  document.getElementById('onb-key').value.trim(),
    model:    document.getElementById('onb-model').value.trim()
  });
  try {
    var r = await fetch('/api/test').then(function(r){ return r.json(); });
    if(r.ok){
      st.style.color = '#3aa655';
      st.textContent = '✓ Connexion établie.';
      var m = await fetch('/api/models').then(function(r){ return r.json(); });
      var list = (m.models || []).slice(0, 200);
      document.getElementById('onb-models').innerHTML =
        list.map(function(x){ return '<option value="' + x + '">'; }).join('');
      if(!document.getElementById('onb-model').value && list.length)
        document.getElementById('onb-model').value = list[0];
    } else {
      st.style.color = '#c0392b';
      st.textContent = '✗ ' + (r.error || ('HTTP ' + (r.status || '?')));
    }
  } catch(e){
    st.style.color = '#c0392b';
    st.textContent = '✗ ' + e;
  }
}

async function onbSave(){
  var st = document.getElementById('onb-status');
  var r = await post('/api/setup', {
    workspace: document.getElementById('onb-ws').value.trim(),
    base_url:  document.getElementById('onb-url').value.trim(),
    api_key:   document.getElementById('onb-key').value.trim(),
    model:     document.getElementById('onb-model').value.trim()
  });
  if(r.error){
    st.style.color = '#c0392b';
    st.textContent = '✗ ' + r.error;
    return;
  }
  location.reload();
}

window.addEventListener('load', async function(){
  try {
    var s = await fetch('/api/setup/state').then(function(r){ return r.json(); });
    if(s.configured) return;
    document.getElementById('onb-prov').innerHTML = ONB_PROVIDERS.map(function(p){
      return '<option value="' + p.id + '">' + p.label + '</option>';
    }).join('');
    document.getElementById('onb-ws').value = s.suggested_workspace;
    onbProv();
    document.getElementById('monb').classList.add('on');
  } catch(e){ /* route absente : patch Python non applique */ }
});
</script>
<!-- ════════ /SB_ONBOARD_PATCH ════════ -->
'''


# ═══════════════════════════════════════════════════════════════════════
#  Moteur
# ═══════════════════════════════════════════════════════════════════════

def patch_python(src: str):
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


def patch_html(src: str):
    if "</body>" not in src:
        return src, [("✗", "Bloc d'accueil", "</body> introuvable")], True
    i = src.rfind("</body>")
    out = src[:i] + ONBOARDING_HTML + "\n" + src[i:]
    return out, [("✓", "Bloc d'accueil injecté avant </body>", "1 insertion")], False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".", help="dossier du dépôt Second Brain")
    ap.add_argument("--dry-run", action="store_true", help="n'écrit rien")
    args = ap.parse_args()

    root = Path(args.dir).resolve()
    py_f, html_f = root / "second_brain.py", root / "ui.html"

    for f in (py_f, html_f):
        if not f.exists():
            print("✗ Introuvable : %s" % f)
            print("  Lancez le script depuis le dossier du dépôt, ou utilisez --dir")
            return 1

    py_src, html_src = py_f.read_text(encoding="utf-8"), html_f.read_text(encoding="utf-8")

    if MARKER in py_src or "SB_ONBOARD_PATCH" in html_src:
        print("⚠ Le patch est déjà appliqué. Rien à faire.")
        print("  Pour repartir de zéro : restaurez les .bak puis relancez.")
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
        print("\n✗ ABANDON — au moins une ancre est introuvable, rien n'a été écrit.")
        print("  Votre version du fichier diffère de celle attendue.")
        print("  Envoyez-moi les lignes marquées ✗ et je vous donne l'ancre adaptée.")
        return 2

    if args.dry_run:
        print("\n(--dry-run : aucun fichier modifié)")
        return 0

    shutil.copy2(py_f, py_f.with_suffix(".py.bak"))
    shutil.copy2(html_f, html_f.with_suffix(".html.bak"))
    py_f.write_text(py_out, encoding="utf-8")
    html_f.write_text(html_out, encoding="utf-8")

    print("\n✓ Patch appliqué.")
    print("  Sauvegardes : second_brain.py.bak, ui.html.bak")
    print("\n  Vérifier :  python second_brain.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
