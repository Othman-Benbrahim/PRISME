"""Mise a jour de l'index d'un vault : incrementale, par fichier et par segment.

- Un fichier n'est relu que si sa date de modification ou sa taille a change,
  et reindexe seulement si son contenu (SHA-256) a change.
- Dans un fichier modifie, seuls les segments dont l'empreinte a change sont
  reecrits ; les autres gardent leur identifiant (utile aux vecteurs de E7).
- Les liens sont re-resolus quand l'ensemble des notes change (ajout, retrait).
- Une reconstruction complete se fait dans un fichier a part, qui remplace
  l'ancien en une operation : l'index en service n'est jamais a moitie ecrit.
"""
import hashlib
import os
import threading
import time
from pathlib import Path

from ..markdown import extract_link_refs, extract_tags
from ..vault import SKIP_DIRS
from . import store
from .resolver import LinkResolver
from .segmenter import segment, title_of

BATCH = 200
SYNC_LIMIT = 5000          # au-dela, les rafraichissements declenches par une requete passent en arriere-plan
MIN_INTERVAL = 2.0         # secondes entre deux verifications du disque


def walk_notes(root):
    """Toutes les notes .md du vault, sans plafond, hors dossiers caches et systeme."""
    root = str(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for fn in sorted(filenames):
            if fn.lower().endswith(".md") and not fn.startswith("."):
                yield os.path.join(dirpath, fn)


def _context_line(content, ref):
    low = ref.lower()
    for line in content.split("\n"):
        if low in line.lower():
            return line.strip()[:150]
    return ""


class VaultIndex:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.db_path = store.db_path_for(self.root)
        self.fts = store.fts5_available()
        self._write = threading.Lock()
        self._readers = 0
        self._readers_cv = threading.Condition()
        self._last_check = 0.0
        self._thread = None
        self.state = "vide"            # vide | construction | pret | erreur
        self.progress = {"done": 0, "total": 0}
        self.error = ""
        self.last_duration = None
        self.file_count = 0
        self._open_schema()

    # ── Connexions ─────────────────────────────────────────────────────
    def _open_schema(self):
        with store.session(self.db_path) as conn:
            if not store.init_schema(conn):
                conn.close()
                self._discard(self.db_path)
                with store.session(self.db_path) as fresh:
                    store.init_schema(fresh)
            else:
                self.file_count = conn.execute("SELECT count(*) FROM files").fetchone()[0]
                self.state = "pret" if self.file_count else "vide"

    @staticmethod
    def _discard(path):
        for suffix in ("", "-journal"):
            try:
                os.remove(str(path) + suffix)
            except FileNotFoundError:
                pass

    def read(self):
        """Contexte de lecture ; la reconstruction attend qu'aucune lecture ne soit en cours."""
        index = self

        class _Reader:
            def __enter__(self_inner):
                with index._readers_cv:
                    index._readers += 1
                self_inner.conn = store.connect(index.db_path)
                return self_inner.conn

            def __exit__(self_inner, *exc):
                self_inner.conn.close()
                with index._readers_cv:
                    index._readers -= 1
                    index._readers_cv.notify_all()
        return _Reader()

    # ── Rafraichissement ───────────────────────────────────────────────
    def ensure_fresh(self):
        """Appele avant une lecture. Petit vault : verification synchrone.
        Grand vault ou premiere construction : en arriere-plan, on sert l'existant."""
        now = time.monotonic()
        if now - self._last_check < MIN_INTERVAL or self._write.locked():
            return
        if self.file_count > SYNC_LIMIT or (self.state == "vide" and not self._small_vault()):
            self.start_background()
            return
        self.refresh(blocking=False)

    def _small_vault(self):
        for n, _ in enumerate(walk_notes(self.root), 1):
            if n > SYNC_LIMIT:
                return False
        return True

    def start_background(self, rebuild=False):
        if self._thread and self._thread.is_alive():
            return False
        target = self.rebuild if rebuild else self.refresh
        self._thread = threading.Thread(target=target, name="prisme-index", daemon=True)
        self._thread.start()
        return True

    def refresh(self, blocking=True):
        if not self._write.acquire(blocking=blocking):
            return None
        try:
            started = time.monotonic()
            with store.session(self.db_path) as conn:
                changed = self._refresh_into(conn, track_state=True)
            self.last_duration = round(time.monotonic() - started, 2)
            return changed
        except Exception as e:                                   # noqa: BLE001
            self.state, self.error = "erreur", f"{type(e).__name__}: {e}"
            print(f"  x Index : {self.error}")
            raise
        finally:
            self._last_check = time.monotonic()
            self._write.release()

    def _refresh_into(self, conn, track_state):
        on_disk = {}
        for p in walk_notes(self.root):
            try:
                st = os.stat(p)
            except OSError:
                continue
            on_disk[p] = (st.st_mtime, st.st_size)
        known = {r["path"]: (r["id"], r["mtime"], r["size"], r["sha256"])
                 for r in conn.execute("SELECT id, path, mtime, size, sha256 FROM files")}
        todo = [p for p, meta in on_disk.items() if p not in known or known[p][1:3] != meta]
        gone = [p for p in known if p not in on_disk]
        set_changed = bool(gone) or any(p not in known for p in todo)

        if track_state:
            self.progress = {"done": 0, "total": len(todo)}
            if todo and self.state != "pret":
                self.state = "construction"

        resolver = LinkResolver(on_disk) if (todo or set_changed) else None
        for p in gone:
            self._delete_file(conn, known[p][0])
        for i, p in enumerate(todo, 1):
            self._index_file(conn, p, on_disk[p], known.get(p), resolver)
            if i % BATCH == 0:
                conn.commit()
                if track_state:
                    self.progress["done"] = i
        if set_changed:
            self._resolve_all(conn, resolver)
        conn.commit()
        self.file_count = len(on_disk)
        if track_state:
            self.progress["done"] = len(todo)
            self.state, self.error = "pret", ""
        return {"indexed": len(todo), "removed": len(gone)}

    def touch(self, *paths):
        """Mise a jour immediate apres une ecriture faite par PRISME."""
        wanted = [str(Path(p).resolve()) for p in paths if p]
        if not wanted:
            return
        with self._write, store.session(self.db_path) as conn:
            set_changed = False
            all_paths = None
            for p in wanted:
                if not p.lower().endswith(".md"):
                    # dossier renomme ou supprime : on laisse le rafraichissement complet s'en charger
                    self._last_check = 0.0
                    continue
                row = conn.execute("SELECT id, mtime, size, sha256 FROM files WHERE path = ?", (p,)).fetchone()
                if os.path.isfile(p):
                    if all_paths is None:
                        all_paths = {r[0] for r in conn.execute("SELECT path FROM files")} | set(wanted)
                        all_paths = {x for x in all_paths if os.path.isfile(x)}
                    st = os.stat(p)
                    known = (row["id"], row["mtime"], row["size"], row["sha256"]) if row else None
                    self._index_file(conn, p, (st.st_mtime, st.st_size), known, LinkResolver(all_paths))
                    set_changed |= row is None
                elif row:
                    self._delete_file(conn, row["id"])
                    set_changed = True
            if set_changed:
                paths_now = [r[0] for r in conn.execute("SELECT path FROM files")]
                self._resolve_all(conn, LinkResolver(paths_now))
            conn.commit()
            if self.state == "vide" and conn.execute("SELECT count(*) FROM files").fetchone()[0]:
                self.state = "pret"

    # ── Un fichier ─────────────────────────────────────────────────────
    def _delete_file(self, conn, file_id):
        if self.fts:
            conn.execute("DELETE FROM segments_fts WHERE rowid IN (SELECT id FROM segments WHERE file_id = ?)",
                         (file_id,))
        conn.execute("DELETE FROM files WHERE id = ?", (file_id,))

    def _index_file(self, conn, path, meta, known, resolver):
        try:
            raw = Path(path).read_bytes()
        except OSError:
            return
        sha = hashlib.sha256(raw).hexdigest()
        mtime, size = meta
        if known and known[3] == sha:                       # contenu identique : dates seulement
            conn.execute("UPDATE files SET mtime = ?, size = ? WHERE id = ?", (mtime, size, known[0]))
            return
        content = raw.decode("utf-8", errors="replace")
        p = Path(path)
        try:
            rel = p.relative_to(self.root).as_posix()
        except ValueError:
            rel = p.name
        title = title_of(content, p.stem)
        now = time.time()
        if known:
            file_id = known[0]
            conn.execute("UPDATE files SET title=?, mtime=?, size=?, sha256=?, indexed_at=? WHERE id=?",
                         (title, mtime, size, sha, now, file_id))
        else:
            file_id = conn.execute(
                "INSERT INTO files(path, rel, name, stem, title, mtime, size, sha256, indexed_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (path, rel, p.name, p.stem, title, mtime, size, sha, now)).lastrowid

        # Segments : on garde ceux dont l'empreinte existe deja
        old = {}
        for r in conn.execute("SELECT id, sha256 FROM segments WHERE file_id = ?", (file_id,)):
            old.setdefault(r["sha256"], []).append(r["id"])
        for ord_, seg in enumerate(segment(content)):
            h = seg.sha256
            if old.get(h):
                seg_id = old[h].pop(0)
                conn.execute("UPDATE segments SET ord=?, start_line=?, end_line=? WHERE id=?",
                             (ord_, seg.start_line, seg.end_line, seg_id))
                continue
            seg_id = conn.execute(
                "INSERT INTO segments(file_id, ord, heading, level, start_line, end_line, text, chars, sha256) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (file_id, ord_, seg.heading, seg.level, seg.start_line, seg.end_line,
                 seg.text, len(seg.text), h)).lastrowid
            if self.fts:
                conn.execute("INSERT INTO segments_fts(rowid, name, heading, text) VALUES (?,?,?,?)",
                             (seg_id, p.stem, seg.heading, seg.text))
        stale = [i for ids in old.values() for i in ids]
        if stale:
            marks = ",".join("?" * len(stale))
            if self.fts:
                conn.execute(f"DELETE FROM segments_fts WHERE rowid IN ({marks})", stale)
            conn.execute(f"DELETE FROM segments WHERE id IN ({marks})", stale)

        conn.execute("DELETE FROM links WHERE file_id = ?", (file_id,))
        conn.executemany(
            "INSERT INTO links(file_id, raw, target_path, context) VALUES (?,?,?,?)",
            [(file_id, ref, resolver.resolve(ref, path) if resolver else None, _context_line(content, ref))
             for ref in sorted(extract_link_refs(content))])
        conn.execute("DELETE FROM tags WHERE file_id = ?", (file_id,))
        conn.executemany("INSERT INTO tags(file_id, tag) VALUES (?,?)",
                         [(file_id, t) for t in sorted(set(extract_tags(content)))])

    def _resolve_all(self, conn, resolver):
        rows = conn.execute("SELECT l.id, l.raw, f.path FROM links l JOIN files f ON f.id = l.file_id").fetchall()
        conn.executemany("UPDATE links SET target_path = ? WHERE id = ?",
                         [(resolver.resolve(r["raw"], r["path"]), r["id"]) for r in rows])

    # ── Reconstruction complete ────────────────────────────────────────
    def rebuild(self):
        with self._write:
            tmp = Path(str(self.db_path) + ".nouveau")
            self._discard(tmp)
            self.state, self.progress = "construction", {"done": 0, "total": 0}
            started = time.monotonic()
            try:
                with store.session(tmp) as conn:
                    store.init_schema(conn)
                    self._refresh_into(conn, track_state=True)
                    self.state = "construction"
                with self._readers_cv:                       # aucune lecture en cours pendant l'echange
                    self._readers_cv.wait_for(lambda: self._readers == 0, timeout=30)
                    os.replace(tmp, self.db_path)
                self.state, self.error = "pret", ""
                self.last_duration = round(time.monotonic() - started, 2)
            except Exception as e:                           # noqa: BLE001
                self._discard(tmp)
                self.state, self.error = "erreur", f"{type(e).__name__}: {e}"
                print(f"  x Reconstruction de l'index : {self.error}")
            finally:
                self._last_check = time.monotonic()

    # ── Etat ───────────────────────────────────────────────────────────
    def status(self):
        with self.read() as conn:
            files = conn.execute("SELECT count(*) FROM files").fetchone()[0]
            segs = conn.execute("SELECT count(*) FROM segments").fetchone()[0]
            links = conn.execute("SELECT count(*), count(target_path) FROM links").fetchone()
        try:
            size = os.path.getsize(self.db_path)
        except OSError:
            size = 0
        return {
            "state": self.state, "error": self.error, "progress": dict(self.progress),
            "vault": str(self.root), "db": str(self.db_path), "db_bytes": size,
            "files": files, "segments": segs, "links": links[0], "links_resolved": links[1],
            "fulltext": "fts5" if self.fts else "like", "last_duration_s": self.last_duration,
        }
