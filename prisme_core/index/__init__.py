"""Index SQLite des notes (etape E2) : recherche, tags, liens, graphe.

L'index est derive des .md : il se reconstruit a tout moment.
"""
import threading
from pathlib import Path

from ..vault import vault_root
from .indexer import VaultIndex

_INDEXES = {}
_LOCK = threading.Lock()


def get_index(root=None):
    """Index du vault donne (le vault courant par defaut)."""
    key = str(Path(root or vault_root()).resolve())
    with _LOCK:
        idx = _INDEXES.get(key)
        if idx is None:
            idx = _INDEXES[key] = VaultIndex(key)
        return idx


def fresh_index():
    idx = get_index()
    idx.ensure_fresh()
    return idx


def notify_changed(*paths):
    """A appeler apres toute ecriture faite par PRISME dans le vault."""
    try:
        get_index().touch(*paths)
    except Exception as e:                    # noqa: BLE001 - l'index ne doit jamais bloquer une ecriture
        print(f"  ! Index : mise a jour differee ({type(e).__name__}: {e})")


def forget_all():
    """Tests : oublie les index ouverts."""
    with _LOCK:
        _INDEXES.clear()
