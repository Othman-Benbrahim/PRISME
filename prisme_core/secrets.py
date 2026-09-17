"""Secrets chiffres au repos (Windows DPAPI).

Sous Windows, une valeur est chiffree pour la session Windows courante :
format stocke "dpapi:<base64>". Ailleurs, elle reste en clair et l'etat
l'indique ; PRISME ne pretend jamais chiffrer quand il ne le fait pas.

Limites assumees (docs/decisions/0023) :
- tout programme lance sous la meme session Windows peut dechiffrer ;
- une valeur chiffree n'est pas lisible sur une autre machine ou un autre compte.
"""
import base64
import json
import sys
import threading

from .paths import DATA_DIR

PREFIX = "dpapi:"
_ENTROPY = b"PRISME-secrets-v1"   # separe nos blobs de ceux des autres applications


class _Dpapi:
    """Appels directs a crypt32.dll, bibliotheque standard uniquement."""

    name = "dpapi"

    def __init__(self):
        import ctypes
        from ctypes import wintypes

        class BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        self._ct, self._BLOB = ctypes, BLOB
        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        args = [ctypes.POINTER(BLOB), wintypes.LPCWSTR, ctypes.POINTER(BLOB),
                ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(BLOB)]
        self._protect = crypt32.CryptProtectData
        self._protect.argtypes = args
        self._protect.restype = wintypes.BOOL
        self._unprotect = crypt32.CryptUnprotectData
        self._unprotect.argtypes = [ctypes.POINTER(BLOB), ctypes.c_void_p] + args[2:]
        self._unprotect.restype = wintypes.BOOL
        self._kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        self._kernel32.LocalFree.restype = ctypes.c_void_p

    def _blob(self, data):
        buf = self._ct.create_string_buffer(data, len(data))
        return self._BLOB(len(data), self._ct.cast(buf, self._ct.POINTER(self._ct.c_char))), buf

    def _call(self, fn, data, *middle):
        ct = self._ct
        blob_in, _keep1 = self._blob(data)
        entropy, _keep2 = self._blob(_ENTROPY)
        out = self._BLOB()
        ok = fn(ct.byref(blob_in), *middle, ct.byref(entropy), None, None, 0x1, ct.byref(out))
        if not ok:
            raise OSError(ct.get_last_error(), "DPAPI a refuse l'operation")
        try:
            return ct.string_at(out.pbData, out.cbData)
        finally:
            self._kernel32.LocalFree(ct.cast(out.pbData, ct.c_void_p))

    def encrypt(self, data: bytes) -> bytes:
        return self._call(self._protect, data, "PRISME")

    def decrypt(self, data: bytes) -> bytes:
        return self._call(self._unprotect, data, None)


def _default_backend():
    if sys.platform != "win32":
        return None
    try:
        return _Dpapi()
    except (OSError, AttributeError):
        return None


# Remplacable dans les tests par un objet ayant encrypt/decrypt/name.
BACKEND = _default_backend()


def available():
    return BACKEND is not None


def protect(value):
    """Chiffre une valeur en clair. Sans DPAPI, la renvoie telle quelle."""
    value = value or ""
    if not value or value.startswith(PREFIX) or BACKEND is None:
        return value
    try:
        return PREFIX + base64.b64encode(BACKEND.encrypt(value.encode("utf-8"))).decode("ascii")
    except OSError as e:
        # Echec du chiffrement : la valeur reste en clair et reveal() le dira ("clair")
        print(f"  ! Chiffrement impossible ({e}) : valeur conservee en clair")
        return value


def reveal(stored):
    """Renvoie (valeur_en_clair, etat). etat : vide | chiffree | clair | illisible."""
    stored = stored or ""
    if not stored:
        return "", "vide"
    if not stored.startswith(PREFIX):
        return stored, "clair"
    if BACKEND is None:
        return "", "illisible"
    try:
        raw = BACKEND.decrypt(base64.b64decode(stored[len(PREFIX):]))
        return raw.decode("utf-8"), "chiffree"
    except (OSError, ValueError):
        return "", "illisible"


# ── Coffre des plugins : ~/.prisme/secrets.json ─────────────────────────
VAULT_FILE = DATA_DIR / "secrets.json"
_LOCK = threading.Lock()


def _load():
    try:
        return json.loads(VAULT_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(data):
    VAULT_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def plugin_secret(plugin_id, name):
    with _LOCK:
        stored = _load().get(plugin_id, {}).get(name, "")
    value, _state = reveal(stored)
    return value


def plugin_secret_states(plugin_id):
    with _LOCK:
        data = _load().get(plugin_id, {})
    return {name: reveal(v)[1] for name, v in data.items()}


def set_plugin_secret(plugin_id, name, value):
    with _LOCK:
        data = _load()
        bucket = data.setdefault(plugin_id, {})
        if value:
            bucket[name] = protect(value)
        else:
            bucket.pop(name, None)
        _save(data)


def forget_plugin(plugin_id):
    with _LOCK:
        data = _load()
        if data.pop(plugin_id, None) is not None:
            _save(data)
