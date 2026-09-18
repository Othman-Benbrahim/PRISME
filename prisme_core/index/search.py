"""Recherche plein texte (FTS5, classement BM25) et requetes derivees de l'index."""
import re

from .store import fts5_available

MARK_OPEN, MARK_CLOSE = "\x01", "\x02"      # balises de surlignage, converties par l'interface
_TOKEN = re.compile(r"\w+", re.UNICODE)


def _scope(root_filter):
    if not root_filter:
        return "", []
    prefix = root_filter.rstrip("/\\")
    return " AND (f.path = ? OR f.path LIKE ? ESCAPE '\\')", [prefix, _like_prefix(prefix)]


def _like_prefix(prefix):
    esc = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    sep = "\\\\" if "\\" in prefix else "/"
    return esc + sep + "%"


def fts_query(text):
    """Chaque mot devient un prefixe obligatoire : « predic ecri » trouve « prédiction … écriture »."""
    tokens = _TOKEN.findall(text or "")
    return " AND ".join('"%s"*' % t.replace('"', "") for t in tokens)


def search(index, text, limit_files=40, per_file=4, root_filter=None):
    query = fts_query(text)
    if not query:
        return []
    scope_sql, scope_args = _scope(root_filter)
    with index.read() as conn:
        if fts5_available() and index.fts:
            rows = conn.execute(
                "SELECT s.file_id, s.start_line, f.path, f.name, f.rel, "
                f"highlight(segments_fts, 1, '{MARK_OPEN}', '{MARK_CLOSE}') AS heading, "
                f"snippet(segments_fts, 2, '{MARK_OPEN}', '{MARK_CLOSE}', '…', 14) AS extrait, "
                "bm25(segments_fts, 4.0, 2.0, 1.0) AS score "
                "FROM segments_fts JOIN segments s ON s.id = segments_fts.rowid "
                "JOIN files f ON f.id = s.file_id "
                "WHERE segments_fts MATCH ?" + scope_sql + " ORDER BY score LIMIT 600",
                [query] + scope_args).fetchall()
        else:
            tokens = _TOKEN.findall(text)
            cond = " AND ".join("(s.text LIKE ? OR s.heading LIKE ? OR f.stem LIKE ?)" for _ in tokens)
            args = [a for t in tokens for a in (f"%{t}%",) * 3]
            rows = conn.execute(
                "SELECT s.file_id, s.heading, s.start_line, f.path, f.name, f.rel, "
                "substr(s.text, 1, 160) AS extrait, 0 AS score FROM segments s "
                "JOIN files f ON f.id = s.file_id WHERE " + cond + scope_sql + " LIMIT 600",
                args + scope_args).fetchall()
    results, by_file = [], {}
    for r in rows:
        entry = by_file.get(r["file_id"])
        if entry is None:
            if len(results) >= limit_files:
                continue
            entry = {"path": r["path"], "name": r["name"], "rel": r["rel"], "score": r["score"], "matches": []}
            by_file[r["file_id"]] = entry
            results.append(entry)
        if len(entry["matches"]) < per_file:
            extrait = " ".join((r["extrait"] or "").split())
            entry["matches"].append({"line": r["start_line"], "heading": r["heading"], "text": extrait})
    return results


def tags(index, root_filter=None):
    scope_sql, scope_args = _scope(root_filter)
    with index.read() as conn:
        rows = conn.execute("SELECT t.tag, f.path FROM tags t JOIN files f ON f.id = t.file_id "
                            "WHERE 1=1" + scope_sql + " ORDER BY f.path", scope_args).fetchall()
    grouped = {}
    for r in rows:
        grouped.setdefault(r["tag"], []).append(r["path"])
    return [{"tag": k, "count": len(v), "files": v}
            for k, v in sorted(grouped.items(), key=lambda x: (-len(x[1]), x[0]))]


def graph(index, root_filter=None):
    scope_sql, scope_args = _scope(root_filter)
    with index.read() as conn:
        files = conn.execute("SELECT f.id, f.path, f.stem, f.rel FROM files f WHERE 1=1" + scope_sql
                             + " ORDER BY f.path", scope_args).fetchall()
        links = conn.execute("SELECT f.path AS src, l.target_path AS dst FROM links l "
                             "JOIN files f ON f.id = l.file_id "
                             "WHERE l.target_path IS NOT NULL AND l.target_path != f.path" + scope_sql,
                             scope_args).fetchall()
    inside = {r["path"] for r in files}
    degree = {p: 0 for p in inside}
    edges, seen = [], set()
    for r in links:
        if r["dst"] not in inside:
            continue
        degree[r["src"]] += 1
        degree[r["dst"]] += 1
        key = tuple(sorted((r["src"], r["dst"])))
        if key not in seen:
            seen.add(key)
            edges.append({"source": r["src"], "target": r["dst"]})
    base = (root_filter or "").rstrip("/\\")
    nodes = []
    for r in files:
        rel = r["path"][len(base):].lstrip("/\\") if base and r["path"].startswith(base) else r["rel"]
        nodes.append({"id": r["path"], "name": r["stem"], "path": r["path"],
                      "degree": degree[r["path"]], "rel": rel})
    return {"nodes": nodes, "links": edges}


def backlinks(index, target, root_filter=None):
    scope_sql, scope_args = _scope(root_filter)
    with index.read() as conn:
        rows = conn.execute(
            "SELECT f.path, f.name, l.context, l.raw FROM links l JOIN files f ON f.id = l.file_id "
            "WHERE l.target_path = ? AND f.path != ?" + scope_sql + " ORDER BY f.path, l.raw",
            [target, target] + scope_args).fetchall()
    out, seen = [], set()
    for r in rows:
        if r["path"] in seen:
            continue
        seen.add(r["path"])
        out.append({"path": r["path"], "name": r["name"], "ctx": r["context"], "ref": r["raw"]})
    return out


def all_paths(index):
    with index.read() as conn:
        return [r[0] for r in conn.execute("SELECT path FROM files")]


def note_meta(index, path):
    """En-tete de provenance d'une note, tel que l'index l'a lu."""
    with index.read() as conn:
        row = conn.execute(
            "SELECT m.* FROM note_meta m JOIN files f ON f.id = m.file_id WHERE f.path = ?",
            (path,)).fetchone()
    return dict(row) if row else {}


def by_prisme_id(index, ident):
    """Chemin et nom de la note portant cet identifiant."""
    if not ident:
        return None
    with index.read() as conn:
        row = conn.execute(
            "SELECT f.path, f.name, f.rel FROM note_meta m JOIN files f ON f.id = m.file_id "
            "WHERE m.prisme_id = ?", (str(ident),)).fetchone()
    return dict(row) if row else None


def notes_generees(index, limit=200):
    """Notes produites par une machine, les plus recentes d'abord."""
    with index.read() as conn:
        rows = conn.execute(
            "SELECT f.path, f.name, f.rel, m.type, m.outil, m.genere_par, m.enregistre_le "
            "FROM note_meta m JOIN files f ON f.id = m.file_id "
            "WHERE m.outil != '' OR m.genere_par != '' "
            "ORDER BY m.enregistre_le DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
