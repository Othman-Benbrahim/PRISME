#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_hardening.py — trois chantiers d'un coup.

  python patch_hardening.py --dry-run
  python patch_hardening.py

1. SERVEUR LOCAL PROTEGE
   Avant : n'importe quelle page web ouverte dans le navigateur pouvait
   parler a 127.0.0.1:5000. Le scenario du DNS rebinding (un domaine hostile
   qui se resout vers 127.0.0.1, donc "meme origine") permettait de lire
   /api/config — c'est-a-dire la cle API — puis d'ecrire dans le vault.
   Apres : l'en-tete Host doit designer localhost, ET toute route /api/
   exige un jeton genere au demarrage, que seule la page servie connait.
   Trappe de sortie : variable d'environnement SECONDBRAIN_NO_AUTH=1.

2. INDEX DE RECHERCHE
   Avant : chaque frappe dans la recherche, chaque ouverture du nuage de
   tags relisait TOUS les .md du vault. Plusieurs secondes a 3000 notes.
   Apres : index en memoire, invalide par date de modification. Seuls les
   fichiers reellement modifies sont relus.

3. INSTANTANE AVANT ECRASEMENT
   Avant : une operation IA destructive ecrasait la note ; l'annulation
   (Ctrl+Alt+Z) vivait dans une variable JS, perdue au rafraichissement.
   Apres : copie de la version precedente dans .trash/versions/, au plus
   une fois toutes les 5 minutes par fichier.

PREREQUIS : patch_onboarding.py, patch_vault.py et patch_streaming.py appliques.
"""
import argparse
import shutil
import sys
from pathlib import Path

MARKER = "SB_HARDENING_PATCH"

# ═══════════════════════════════════════════════════════════════════════
#  1 + 2 + 3 : helpers serveur, inseres avant MAX_SCAN
# ═══════════════════════════════════════════════════════════════════════

OLD_ANCHOR = "MAX_SCAN = 5000"

NEW_HELPERS = '''# --- ''' + MARKER + ''' ---
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
# --- ''' + MARKER + ''' ---

''' + OLD_ANCHOR

# ═══════════════════════════════════════════════════════════════════════
#  save_file : instantane avant ecriture
# ═══════════════════════════════════════════════════════════════════════

OLD_SAVE = '''        p = safe_path(d.get("path", ""))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(d.get("content", ""), encoding="utf-8")
        return jsonify({"ok": True})'''

NEW_SAVE = '''        p = safe_path(d.get("path", ""))
        p.parent.mkdir(parents=True, exist_ok=True)
        snap = snapshot(p)                      # version precedente -> .trash/versions/
        p.write_text(d.get("content", ""), encoding="utf-8")
        return jsonify({"ok": True, "snapshot": str(snap) if snap else None})'''

# ═══════════════════════════════════════════════════════════════════════
#  Recherche et tags via l'index
# ═══════════════════════════════════════════════════════════════════════

OLD_SEARCH = '''    results, total = [], 0
    for f in sorted(iter_md(dir_p)):
        try:
            content = f.read_text(encoding="utf-8")
            if query.lower() not in content.lower(): continue
            matches = []
            for i, line in enumerate(content.split("\\n")):
                if query.lower() in line.lower():
                    matches.append({"line": i+1, "text": line[:140].strip()})
                    if len(matches) >= 4: break
            results.append({"path": str(f), "name": f.name,
                             "rel": str(f.relative_to(Path(dir_p))), "matches": matches})
            total += 1
            if total >= 40: break
        except: pass'''

NEW_SEARCH = '''    results, total = [], 0
    ql = query.lower()
    idx = index_refresh(dir_p)
    for sp in sorted(idx):
        entry = idx[sp]
        if ql not in entry["lower"]: continue
        f = Path(sp)
        matches = []
        for i, line in enumerate(entry["text"].split("\\n")):
            if ql in line.lower():
                matches.append({"line": i+1, "text": line[:140].strip()})
                if len(matches) >= 4: break
        try:    rel = str(f.relative_to(Path(dir_p)))
        except Exception: rel = f.name
        results.append({"path": sp, "name": f.name, "rel": rel, "matches": matches})
        total += 1
        if total >= 40: break'''

OLD_TAGS = '''    tags = {}
    for f in sorted(iter_md(dir_p)):
        try:
            for tag in extract_tags(f.read_text(encoding="utf-8")):
                tags.setdefault(tag, []).append(str(f))
        except: pass'''

NEW_TAGS = '''    tags = {}
    idx = index_refresh(dir_p)
    for sp in sorted(idx):
        for tag in idx[sp]["tags"]:
            tags.setdefault(tag, []).append(sp)'''

PY_EDITS = [
    (OLD_ANCHOR, NEW_HELPERS, "Jeton local + garde Host + index + instantanés"),
    (OLD_SAVE, NEW_SAVE, "save_file : instantané avant écrasement"),
    (OLD_SEARCH, NEW_SEARCH, "/api/search via l'index"),
    (OLD_TAGS, NEW_TAGS, "/api/tags via l'index"),
]

# ═══════════════════════════════════════════════════════════════════════
#  Client : jeton ajoute a chaque appel /api/
# ═══════════════════════════════════════════════════════════════════════

HTML_ANCHOR = "<!-- ════════ /SB_STREAM_PATCH ════════ -->"

CLIENT_BLOCK = HTML_ANCHOR + '''

<!-- ════════ ''' + MARKER + ''' — jeton d'accès local ════════ -->
<script>
(function(){
  var _rawFetch = window.fetch.bind(window);
  var SBTOK = null;

  // Recupere le jeton une seule fois, avec l'appel brut (non enveloppe).
  var SBTOK_READY = _rawFetch('/api/token')
    .then(function(r){ return r.json(); })
    .then(function(j){ SBTOK = j && j.token; return SBTOK; })
    .catch(function(){ return null; });

  window.fetch = async function(input, init){
    var url = (typeof input === 'string') ? input
            : (input && input.url) ? input.url : '';
    if(url.indexOf('/api/') !== 0 || url === '/api/token'){
      return _rawFetch(input, init);
    }
    if(!SBTOK){ await SBTOK_READY; }
    init = init || {};
    var h = new Headers(init.headers || {});
    if(SBTOK) h.set('X-SB-Token', SBTOK);
    init.headers = h;
    return _rawFetch(input, init);
  };
})();
</script>
<!-- ════════ /''' + MARKER + ''' ════════ -->'''


def patch_python(src):
    report, out, failed = [], src, False
    for anchor, repl, label in PY_EDITS:
        n = out.count(anchor)
        if n != 1:
            report.append(("✗", label, "ancre introuvable" if n == 0 else "%d occurrences" % n))
            failed = True
            continue
        out = out.replace(anchor, repl)
        report.append(("✓", label, "1 remplacement"))
    return out, report, failed


def patch_html(src):
    n = src.count(HTML_ANCHOR)
    if n != 1:
        return src, [("✗", "Bloc client du jeton",
                      "ancre introuvable" if n == 0 else "%d occurrences" % n)], True
    return src.replace(HTML_ANCHOR, CLIENT_BLOCK), \
           [("✓", "fetch() enveloppé — jeton sur chaque appel /api/", "1 insertion")], False


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
    for need, who in (("SB_VAULT_PATCH", "patch_vault.py"),
                      ("SB_STREAM_PATCH", "patch_streaming.py")):
        if need not in py_src and need not in html_src:
            print("✗ %s n'a pas été appliqué. Lancez-le d'abord." % who)
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

    shutil.copy2(py_f, py_f.with_suffix(".py.bak6"))
    shutil.copy2(html_f, html_f.with_suffix(".html.bak6"))
    py_f.write_text(py_out, encoding="utf-8")
    html_f.write_text(html_out, encoding="utf-8")
    print("\n✓ Patch appliqué.  Sauvegardes : second_brain.py.bak6, ui.html.bak6")
    print("\n  IMPORTANT : rechargez avec Ctrl+Maj+R. Un cache de l'ancienne page")
    print("  n'enverrait pas le jeton et recevrait des 403 sur tous les appels.")
    print("  En cas de blocage :  set SECONDBRAIN_NO_AUTH=1  puis relancer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
