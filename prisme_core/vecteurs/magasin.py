"""Magasin des vecteurs : une base à part, indexée par empreinte de segment.

**Pourquoi pas dans la base de l'index ?** L'index se reconstruit tout seul dès que
`SCHEMA_VERSION` change (docs/decisions/0010) — c'est voulu, il est dérivé des `.md` et
se refait en quelques secondes. Les vecteurs, eux, coûtent des minutes et parfois de
l'argent. Les loger dans la même base, ce serait les perdre à chaque évolution des règles
d'extraction. Ils vivent donc à côté, indexés par **empreinte de segment** (`sha256`) :
un segment qui n'a pas changé garde son vecteur, quel que soit le sort de l'index.

Un seul modèle par magasin (docs/decisions/0019) : la signature du fournisseur est
enregistrée, et en changer vide le magasin après un avertissement explicite.
"""
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from ..paths import DATA_DIR
from . import quantification as quant

DOSSIER = DATA_DIR / "vecteurs"
SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (cle TEXT PRIMARY KEY, valeur TEXT);
CREATE TABLE IF NOT EXISTS vecteurs (
    sha256    TEXT PRIMARY KEY,
    bits      BLOB NOT NULL,
    flottants BLOB NOT NULL,
    vu_le     REAL NOT NULL
);
"""

_VERROU = threading.Lock()


def chemin_pour(racine):
    """Même empreinte de vault que l'index, pour que les deux bases se correspondent."""
    from ..index.store import db_path_for
    DOSSIER.mkdir(parents=True, exist_ok=True)
    return DOSSIER / (db_path_for(racine).stem + ".db")


def _connecter(chemin):
    conn = sqlite3.connect(str(chemin), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = DELETE")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.executescript(SCHEMA)
    conn.execute("PRAGMA user_version = %d" % SCHEMA_VERSION)
    return conn


class Magasin:
    """Vecteurs d'un vault. Les bits sont gardés en mémoire ; les flottants sur disque."""

    def __init__(self, racine):
        self.racine = str(Path(racine).resolve())
        self.chemin = chemin_pour(self.racine)
        self._bits = None                  # [(sha256, entier)] — cache de preselection
        self._verrou = threading.Lock()

    @contextmanager
    def session(self):
        conn = _connecter(self.chemin)
        try:
            yield conn
        finally:
            conn.close()

    # ── Signature ────────────────────────────────────────────────────────
    def signature(self):
        with self.session() as conn:
            r = conn.execute("SELECT valeur FROM meta WHERE cle='signature'").fetchone()
        return r["valeur"] if r else ""

    def fixer_signature(self, signature):
        """Pose la signature. Si elle change, le magasin est vidé : pas de mélange (0019)."""
        with self._verrou:
            actuelle = self.signature()
            with self.session() as conn:
                if actuelle and actuelle != signature:
                    conn.execute("DELETE FROM vecteurs")
                conn.execute("INSERT OR REPLACE INTO meta (cle, valeur) VALUES ('signature', ?)",
                             [signature])
                conn.commit()
            if actuelle and actuelle != signature:
                self._bits = None
                return True                # revectorisation nécessaire
        return False

    # ── Écriture ─────────────────────────────────────────────────────────
    def enregistrer(self, couples):
        """`couples` : [(sha256, vecteur)]. Le vecteur est normalisé avant stockage."""
        import time
        maintenant = time.time()
        lignes = []
        for sha, vecteur in couples:
            unitaire = quant.normaliser(vecteur)
            lignes.append((sha, quant.binariser(unitaire).to_bytes((len(unitaire) + 7) // 8, "little"),
                           quant.vers_octets(unitaire), maintenant))
        if not lignes:
            return 0
        with self._verrou, self.session() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO vecteurs (sha256, bits, flottants, vu_le) VALUES (?,?,?,?)",
                lignes)
            conn.commit()
            self._bits = None
        return len(lignes)

    def oublier_absents(self, shas_vivants):
        """Retire les vecteurs de segments qui n'existent plus dans le vault."""
        vivants = set(shas_vivants)
        with self._verrou, self.session() as conn:
            connus = [r["sha256"] for r in conn.execute("SELECT sha256 FROM vecteurs")]
            morts = [s for s in connus if s not in vivants]
            conn.executemany("DELETE FROM vecteurs WHERE sha256 = ?", [(s,) for s in morts])
            conn.commit()
            if morts:
                self._bits = None
        return len(morts)

    def vider(self):
        with self._verrou, self.session() as conn:
            conn.execute("DELETE FROM vecteurs")
            conn.commit()
            self._bits = None

    # ── Lecture ──────────────────────────────────────────────────────────
    def connus(self):
        with self.session() as conn:
            return {r["sha256"] for r in conn.execute("SELECT sha256 FROM vecteurs")}

    def compte(self):
        with self.session() as conn:
            return conn.execute("SELECT count(*) AS n FROM vecteurs").fetchone()["n"]

    def bits(self):
        """Tous les vecteurs binaires, en mémoire. 48 octets par segment : négligeable."""
        with self._verrou:
            if self._bits is None:
                with self.session() as conn:
                    self._bits = [(r["sha256"], int.from_bytes(r["bits"], "little"))
                                  for r in conn.execute("SELECT sha256, bits FROM vecteurs")]
            return self._bits

    def flottants(self, shas):
        """Vecteurs complets de quelques segments, pour le rescoring exact."""
        shas = list(shas)
        if not shas:
            return []
        out = []
        with self.session() as conn:
            for debut in range(0, len(shas), 400):        # SQLite plafonne les paramètres
                tranche = shas[debut:debut + 400]
                marques = ",".join("?" * len(tranche))
                for r in conn.execute(
                        "SELECT sha256, flottants FROM vecteurs WHERE sha256 IN (%s)" % marques,
                        tranche):
                    out.append((r["sha256"], quant.depuis_octets(r["flottants"])))
        return out

    def etat(self):
        return {"chemin": str(self.chemin), "signature": self.signature(),
                "vecteurs": self.compte()}


_MAGASINS = {}
_CACHE_VERROU = threading.Lock()


def magasin_pour(racine=None):
    from ..vault import vault_root
    cle = str(Path(racine or vault_root()).resolve())
    with _CACHE_VERROU:
        m = _MAGASINS.get(cle)
        if m is None:
            m = _MAGASINS[cle] = Magasin(cle)
        return m


def oublier_tout():
    """Tests : referme les magasins ouverts."""
    with _CACHE_VERROU:
        _MAGASINS.clear()
