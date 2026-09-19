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

# Plafond des fichiers d'interface : un fichier plus long redevient monolithique.
PLAFOND_FICHIER = 20_000


def taille_logique(chemin):
    """Taille d'un fichier texte **indépendante de la convention de fin de ligne**.

    `stat().st_size` compte les octets du disque. Git en mode `autocrlf` écrit `\\r\\n`
    sous Windows, ce qui ajoute un octet par ligne : `core.css` pesait 19 801 octets
    sous Linux et 20 091 sous Windows — exactement ses 290 lignes d'écart — et le
    plafond de 20 000 sautait sur une machine et pas sur l'autre.

    Un fichier ne devient pas monolithique parce que le système écrit ses retours à la
    ligne sur deux octets. On mesure donc le texte, retours à la ligne normalisés.
    """
    return len(Path(chemin).read_text(encoding="utf-8"))


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
    from prisme_core import config, index, vault
    vault._LAST_SNAP.clear()
    index.forget_all()          # les fichiers ont change hors de PRISME : index relu
    config.wr_cfg({"workspace": str(VAULT), "configured": True,
                   "base_url": "http://127.0.0.1:9/v1", "model": "m"})
