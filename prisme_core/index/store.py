"""Base SQLite de l'index : emplacement, schema, connexions (docs/decisions/0010).

La base vit dans le profil : ~/.prisme/index/<empreinte du chemin du vault>.db.
Elle ne contient que des donnees derivees des .md : on peut toujours la supprimer.
"""
import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from ..paths import DATA_DIR

# Toute evolution du schema OU des regles d'extraction (segments, tags, liens)
# doit incrementer ce numero : l'index existant est alors reconstruit tout seul.
SCHEMA_VERSION = 2
INDEX_DIR = DATA_DIR / "index"
MAP_FILE = INDEX_DIR / "vaults.json"
_MAP_LOCK = threading.Lock()

_FTS_OK = None


def fts5_available():
    global _FTS_OK
    if _FTS_OK is None:
        try:
            c = sqlite3.connect(":memory:")
            c.execute("CREATE VIRTUAL TABLE t USING fts5(a)")
            c.close()
            _FTS_OK = True
        except sqlite3.OperationalError:
            _FTS_OK = False
    return _FTS_OK


def db_path_for(root):
    root = str(Path(root).resolve())
    key = hashlib.sha256(root.encode("utf-8")).hexdigest()[:16]
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    with _MAP_LOCK:
        try:
            mapping = json.loads(MAP_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            mapping = {}
        if mapping.get(key) != root:
            mapping[key] = root
            MAP_FILE.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")
    return INDEX_DIR / f"{key}.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS files (
    id         INTEGER PRIMARY KEY,
    path       TEXT NOT NULL UNIQUE,
    rel        TEXT NOT NULL,
    name       TEXT NOT NULL,
    stem       TEXT NOT NULL,
    title      TEXT NOT NULL,
    mtime      REAL NOT NULL,
    size       INTEGER NOT NULL,
    sha256     TEXT NOT NULL,
    indexed_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS segments (
    id         INTEGER PRIMARY KEY,
    file_id    INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    ord        INTEGER NOT NULL,
    heading    TEXT NOT NULL,
    level      INTEGER NOT NULL,
    start_line INTEGER NOT NULL,
    end_line   INTEGER NOT NULL,
    text       TEXT NOT NULL,
    chars      INTEGER NOT NULL,
    sha256     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS segments_file ON segments(file_id);
CREATE INDEX IF NOT EXISTS segments_sha ON segments(sha256);
CREATE TABLE IF NOT EXISTS note_meta (
    file_id       INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
    prisme_id     TEXT,
    type          TEXT NOT NULL DEFAULT '',
    outil         TEXT NOT NULL DEFAULT '',
    genere_par    TEXT NOT NULL DEFAULT '',
    preset        TEXT NOT NULL DEFAULT '',
    enregistre_le TEXT NOT NULL DEFAULT '',
    invalide_le   TEXT NOT NULL DEFAULT '',
    parent        TEXT NOT NULL DEFAULT '',
    sources       TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS note_meta_id ON note_meta(prisme_id);
CREATE TABLE IF NOT EXISTS links (
    id          INTEGER PRIMARY KEY,
    file_id     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    raw         TEXT NOT NULL,
    target_path TEXT,
    context     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS links_file ON links(file_id);
CREATE INDEX IF NOT EXISTS links_target ON links(target_path);
CREATE TABLE IF NOT EXISTS tags (
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    tag     TEXT NOT NULL,
    PRIMARY KEY (file_id, tag)
);
CREATE INDEX IF NOT EXISTS tags_tag ON tags(tag);
"""

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS segments_fts USING fts5(
    name, heading, text, tokenize = 'unicode61 remove_diacritics 2'
);
"""


def connect(path):
    conn = sqlite3.connect(str(path), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = DELETE")   # un seul fichier : remplacable en une operation
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_schema(conn):
    """Cree le schema. Renvoie False si la base existante a un autre schema."""
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    has_tables = conn.execute("SELECT count(*) FROM sqlite_master WHERE name='files'").fetchone()[0]
    if has_tables and version != SCHEMA_VERSION:
        return False
    conn.executescript(SCHEMA)
    if fts5_available():
        conn.executescript(FTS_SCHEMA)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()
    return True


@contextmanager
def session(path):
    conn = connect(path)
    try:
        yield conn
    finally:
        conn.close()
