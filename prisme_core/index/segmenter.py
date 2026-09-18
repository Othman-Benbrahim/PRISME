"""Decoupage structurel d'une note en segments (docs/decisions/0011).

- Un segment par titre de niveau 1 a 3 ; les niveaux plus profonds restent dans
  le segment de leur parent.
- Note sans titre : paragraphes regroupes jusqu'a ~1 500 caracteres.
- Section trop longue (> ~4 000 caracteres) : redecoupee entre deux paragraphes ;
  un paragraphe geant est coupe en fin de phrase ; un bloc de code n'est jamais coupe.
- L'en-tete YAML (frontmatter) n'est pas indexe comme texte.
Les numeros de ligne commencent a 1 et se rapportent au fichier complet.
"""
import hashlib
import re
from dataclasses import dataclass

GROUP_TARGET = 1500
SECTION_MAX = 4000
MAX_LEVEL = 3

_ATX = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*#*[ \t]*$")
_SETEXT = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


@dataclass
class Segment:
    heading: str        # chemin des titres, "Titre > Sous-titre"
    level: int          # niveau du titre qui ouvre le segment (0 : sans titre)
    start_line: int
    end_line: int
    text: str

    @property
    def sha256(self):
        return hashlib.sha256(f"{self.heading}\n{self.text}".encode("utf-8")).hexdigest()


def _frontmatter_end(lines):
    """Index de la premiere ligne apres le frontmatter (0 s'il n'y en a pas)."""
    if not lines or lines[0].strip() != "---":
        return 0
    for i in range(1, min(len(lines), 400)):
        if lines[i].strip() in ("---", "..."):
            return i + 1
    return 0


def _blocks(lines, first):
    """Decoupe en blocs : titres, paragraphes, blocs de code.
    Renvoie des tuples (type, debut, fin, lignes, niveau, titre)."""
    out = []
    i, n = first, len(lines)
    para = []
    para_start = None

    def flush(end):
        nonlocal para, para_start
        if para:
            out.append(("para", para_start, end, para, 0, ""))
        para, para_start = [], None

    while i < n:
        line = lines[i]
        fence = _FENCE.match(line)
        if fence:
            flush(i - 1)
            marker = fence.group(1)
            start = i
            i += 1
            while i < n:
                close = _FENCE.match(lines[i])
                if close and close.group(1)[0] == marker[0] and len(close.group(1)) >= len(marker) \
                        and not lines[i].strip()[len(close.group(1)):].strip():
                    break
                i += 1
            end = min(i, n - 1)
            out.append(("code", start, end, lines[start:end + 1], 0, ""))
            i = end + 1
            continue
        atx = _ATX.match(line)
        if atx:
            flush(i - 1)
            out.append(("heading", i, i, [line], len(atx.group(1)), (atx.group(2) or "").strip()))
            i += 1
            continue
        if para and _SETEXT.match(line) and len(para) >= 1:
            # la derniere ligne du paragraphe devient un titre (CommonMark)
            title = para.pop().strip()
            title_line = para_start + len(para)
            flush(title_line - 1)
            level = 1 if line.strip().startswith("=") else 2
            out.append(("heading", title_line, i, [title], level, title))
            i += 1
            continue
        if not line.strip():
            flush(i - 1)
        else:
            if not para:
                para_start = i
            para.append(line)
        i += 1
    flush(n - 1)
    return out


def _split_long(text):
    """Coupe un paragraphe geant en fins de phrase."""
    parts, current = [], ""
    for sentence in _SENTENCE_END.split(text):
        if current and len(current) + len(sentence) + 1 > SECTION_MAX:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}" if current else sentence
    if current:
        parts.append(current)
    return parts


def _pack(blocks, heading, level, target):
    """Regroupe des blocs (debut, fin, texte, est_code) en segments d'au plus `target` caracteres."""
    segments, buf, start, end = [], [], None, None

    def emit():
        nonlocal buf, start, end
        if buf:
            segments.append(Segment(heading, level, start + 1, end + 1, "\n\n".join(buf)))
        buf, start, end = [], None, None

    for b_start, b_end, text, is_code in blocks:
        pieces = [text] if is_code or len(text) <= SECTION_MAX else _split_long(text)
        for piece in pieces:
            size = sum(len(x) + 2 for x in buf)
            if buf and size + len(piece) > target:
                emit()
            if start is None:
                start = b_start
            buf.append(piece)
            end = b_end
    emit()
    return segments


def _block_text(kind, blines):
    return "\n".join(blines) if kind == "code" else "\n".join(x.rstrip() for x in blines).strip()


def segment(content):
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks = _blocks(lines, _frontmatter_end(lines))
    has_headings = any(b[0] == "heading" and b[4] <= MAX_LEVEL for b in blocks)

    if not has_headings:
        body = [(start, end, _block_text(kind, blines), kind == "code")
                for kind, start, end, blines, _lv, _t in blocks]
        return [s for s in _pack(body, "", 0, GROUP_TARGET) if s.text.strip()]

    sections = []            # (titre, niveau, ligne_titre, blocs)
    stack = []               # [(niveau, titre)]
    current = ("", 0, None, [])
    for kind, start, end, blines, level, title in blocks:
        if kind == "heading" and level <= MAX_LEVEL:
            sections.append(current)
            stack = [(lv, t) for lv, t in stack if lv < level] + [(level, title)]
            path = " > ".join(t for _, t in stack if t)
            current = (path, level, start, [])
            continue
        current[3].append((start, end, _block_text(kind, blines), kind == "code"))
    sections.append(current)

    out = []
    for path, level, heading_line, body in sections:
        if not body:
            if path:
                out.append(Segment(path, level, heading_line + 1, heading_line + 1, ""))
            continue
        packed = _pack(body, path, level, SECTION_MAX)
        if heading_line is not None and packed:
            packed[0].start_line = min(packed[0].start_line, heading_line + 1)
        out.extend(packed)
    return out


def title_of(content, fallback):
    lines = content.replace("\r\n", "\n").split("\n")
    for kind, _s, _e, _l, level, title in _blocks(lines, _frontmatter_end(lines)):
        if kind == "heading" and level == 1 and title:
            return title
    return fallback
