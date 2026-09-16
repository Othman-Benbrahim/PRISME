"""Index de recherche en memoire, invalide par date de modification."""
import threading

from .markdown import extract_tags
from .vault import iter_md

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
