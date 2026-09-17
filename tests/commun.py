"""Environnement de test partage : profil et vault isoles, crees AVANT l'import de prisme_core."""
import base64
import os
import sys
import tempfile
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="prisme-test-"))
os.environ["PRISME_DATA_DIR"] = str(TMP / "profil")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VAULT = TMP / "vault"


class FakeCipher:
    """Remplace DPAPI hors Windows : reversible, mais jamais en clair dans le fichier."""
    name = "faux"

    def encrypt(self, data):
        return base64.b85encode(bytes(b ^ 0x5A for b in data))

    def decrypt(self, data):
        return bytes(b ^ 0x5A for b in base64.b85decode(data))


def reset_vault():
    import shutil
    shutil.rmtree(VAULT, ignore_errors=True)
    (VAULT / "sous").mkdir(parents=True)
    (VAULT / "Alpha.md").write_text("# Alpha\n\n[[Beta]] #t1\n\nmot-unique\n", encoding="utf-8")
    (VAULT / "sous" / "Beta.md").write_text("# Beta\n\n[[Alpha]]\n", encoding="utf-8")
    from prisme_core import config
    config.wr_cfg({"workspace": str(VAULT), "configured": True,
                   "base_url": "http://127.0.0.1:9/v1", "model": "m"})
