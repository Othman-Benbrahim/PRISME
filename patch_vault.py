#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_vault.py — confine les operations fichiers a l'espace de travail,
et remplace la suppression definitive par une corbeille.

  python patch_vault.py --dry-run
  python patch_vault.py

PROBLEME CORRIGE
  /api/files/read, save, new, rename et delete acceptaient n'importe quel
  chemin absolu du disque. delete faisait meme un shutil.rmtree() sans
  confirmation. Un bug d'interface, un plugin maladroit ou une page web
  malveillante pouvait donc effacer un dossier hors du vault.

APRES LE PATCH
  - lecture / ecriture / creation / renommage / suppression : uniquement
    sous le dossier de notes configure ;
  - suppression = deplacement vers <vault>/.trash/AAAA-MM-JJ/ ;
  - la NAVIGATION (/api/files) reste libre : il faut pouvoir parcourir le
    disque pour choisir un nouvel espace de travail.

PREREQUIS : patch_onboarding.py applique.
"""
import argparse
import shutil
import sys
from pathlib import Path

MARKER = "# --- SB_VAULT_PATCH ---"

# ═══════════════════════════════════════════════════════════════════════
#  Helpers, inseres avant MAX_SCAN (pose par patch_onboarding.py)
# ═══════════════════════════════════════════════════════════════════════

OLD_ANCHOR = "MAX_SCAN = 5000"

NEW_HELPERS = MARKER + '''
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
''' + MARKER + '''

''' + OLD_ANCHOR

# ═══════════════════════════════════════════════════════════════════════
#  Routes fichiers
# ═══════════════════════════════════════════════════════════════════════

OLD_READ = '''@app.route("/api/files/read", methods=["GET"])
def read_file():
    try: return jsonify({"content": Path(request.args.get("path", "")).read_text(encoding="utf-8")})
    except Exception as e: return jsonify({"error": str(e)}), 500'''

NEW_READ = '''@app.route("/api/files/read", methods=["GET"])
def read_file():
    try:
        p = safe_path(request.args.get("path", ""))
        # errors="replace" : une note en CP-1252 ne doit pas faire echouer la lecture
        return jsonify({"content": p.read_text(encoding="utf-8", errors="replace")})
    except (PermissionError, FileNotFoundError) as e: return _path_err(e)
    except Exception as e: return jsonify({"error": str(e)}), 500'''

OLD_SAVE = '''@app.route("/api/files/save", methods=["POST"])
def save_file():
    d = request.json
    try:
        Path(d["path"]).write_text(d.get("content", ""), encoding="utf-8")
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500'''

NEW_SAVE = '''@app.route("/api/files/save", methods=["POST"])
def save_file():
    d = request.json or {}
    try:
        p = safe_path(d.get("path", ""))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(d.get("content", ""), encoding="utf-8")
        return jsonify({"ok": True})
    except (PermissionError, FileNotFoundError) as e: return _path_err(e)
    except Exception as e: return jsonify({"error": str(e)}), 500'''

OLD_NEW = '''@app.route("/api/files/new", methods=["POST"])
def new_file():
    d = request.json
    dir_p = d.get("dir", rd_cfg().get("workspace", str(Path.home())))
    name  = d.get("name", "nouveau.md")
    if not name.endswith(".md"): name += ".md"
    path = Path(dir_p) / name
    if path.exists(): return jsonify({"error": "Fichier existant"}), 409
    try:
        path.write_text(f"# {name.replace('.md','')}\\n\\n", encoding="utf-8")
        return jsonify({"ok": True, "path": str(path)})
    except Exception as e: return jsonify({"error": str(e)}), 500'''

NEW_NEW = '''@app.route("/api/files/new", methods=["POST"])
def new_file():
    d = request.json or {}
    name = (d.get("name") or "nouveau.md").strip()
    if any(c in name for c in '\\\\/:*?"<>|'):
        return jsonify({"error": "Nom de fichier invalide"}), 400
    if not name.endswith(".md"): name += ".md"
    try:
        dir_p = safe_path(d.get("dir") or rd_cfg().get("workspace", ""))
        path  = safe_path(dir_p / name)
    except (PermissionError, FileNotFoundError) as e: return _path_err(e)
    if path.exists(): return jsonify({"error": "Fichier existant"}), 409
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {name.replace('.md','')}\\n\\n", encoding="utf-8")
        return jsonify({"ok": True, "path": str(path)})
    except Exception as e: return jsonify({"error": str(e)}), 500'''

OLD_RENAME = '''    old = Path(d.get("old", "")); new_name = d.get("new_name", "")
    if not old.exists() or not new_name: return jsonify({"error": "Paramètres invalides"}), 400
    new_path = old.parent / new_name'''

NEW_RENAME = '''    try:
        old = safe_path(d.get("old", ""))
    except (PermissionError, FileNotFoundError) as e: return _path_err(e)
    new_name = (d.get("new_name") or "").strip()
    if not old.exists() or not new_name: return jsonify({"error": "Paramètres invalides"}), 400
    if any(c in new_name for c in '\\\\/:*?"<>|'):
        return jsonify({"error": "Nom de fichier invalide"}), 400
    new_path = old.parent / new_name'''

OLD_DELETE = '''@app.route("/api/files/delete", methods=["POST"])
def delete_file():
    path = request.json.get("path", "")
    try:
        p = Path(path)
        if p.is_dir(): shutil.rmtree(p)
        else: p.unlink()
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500'''

NEW_DELETE = '''@app.route("/api/files/delete", methods=["POST"])
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
    except Exception as e: return jsonify({"error": str(e)}), 500'''

PY_EDITS = [
    (OLD_ANCHOR, NEW_HELPERS, 1, "Helpers vault_root / safe_path / to_trash"),
    (OLD_READ, NEW_READ, 1, "/api/files/read confiné (+ encodage tolérant)"),
    (OLD_SAVE, NEW_SAVE, 1, "/api/files/save confiné"),
    (OLD_NEW, NEW_NEW, 1, "/api/files/new confiné + nom validé"),
    (OLD_RENAME, NEW_RENAME, 1, "/api/files/rename confiné + nom validé"),
    (OLD_DELETE, NEW_DELETE, 1, "/api/files/delete → corbeille .trash/"),
]

# ── ui.html : message de suppression adapte ────────────────────────────
OLD_TOAST = "loadDir(CUR_DIR); toast('🗑 Supprimé');"
NEW_TOAST = "loadDir(CUR_DIR); toast(r.trashed?'🗑 Déplacé vers la corbeille (.trash)':'🗑 Supprimé définitivement');"


def patch_python(src):
    report, out, failed = [], src, False
    for anchor, repl, expected, label in PY_EDITS:
        n = out.count(anchor)
        if n != expected:
            report.append(("✗", label, "ancre introuvable" if n == 0 else "%d occurrences" % n))
            failed = True
            continue
        out = out.replace(anchor, repl)
        report.append(("✓", label, "1 remplacement"))
    return out, report, failed


def patch_html(src):
    n = src.count(OLD_TOAST)
    if n != 1:
        return src, [("⚠", "Message de suppression (ui.html)",
                      "ancre absente — sans effet fonctionnel, le patch Python suffit")], False
    return src.replace(OLD_TOAST, NEW_TOAST), \
           [("✓", "Message de suppression mentionne la corbeille", "1 remplacement")], False


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
        print("⚠ Déjà appliqué. Rien à faire.")
        return 0

    py_out, py_rep, py_fail = patch_python(py_src)
    html_out, html_rep, _ = patch_html(html_src)

    print("\n── second_brain.py " + "─" * 42)
    for m, l, d in py_rep:
        print("  %s %-52s %s" % (m, l, d))
    print("\n── ui.html " + "─" * 50)
    for m, l, d in html_rep:
        print("  %s %-52s %s" % (m, l, d))

    if py_fail:
        print("\n✗ ABANDON — rien n'a été écrit.")
        print("  Envoyez-moi les routes marquées ✗ telles qu'elles sont chez vous.")
        return 2
    if args.dry_run:
        print("\n(--dry-run : aucun fichier modifié)")
        return 0

    shutil.copy2(py_f, py_f.with_suffix(".py.bak4"))
    shutil.copy2(html_f, html_f.with_suffix(".html.bak4"))
    py_f.write_text(py_out, encoding="utf-8")
    html_f.write_text(html_out, encoding="utf-8")
    print("\n✓ Patch appliqué.  Sauvegardes : second_brain.py.bak4, ui.html.bak4")
    return 0


if __name__ == "__main__":
    sys.exit(main())
