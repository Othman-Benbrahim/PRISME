"""Analyse Markdown : liens, resolution de references, tags."""
import re
import uuid
from pathlib import Path

def _id(): return str(uuid.uuid4())[:8]

def _node(t, c="", ch=None):
    return {"id": _id(), "title": t, "content": c, "children": ch or [], "collapsed": False}

def extract_wikilinks(content):
    """Compatibilité — délègue à extract_link_refs."""
    return list(extract_link_refs(content))

_RE_WIKI    = re.compile(r"\[\[([^\]|#\n]+?)(?:[|#][^\]\n]*?)?\]\]")

_RE_MDLINK  = re.compile(r"\[[^\]\n]*\]\(\s*([^)\s#?]+?\.md)(?:[#?][^)]*)?\s*\)")

_RE_QUOTED  = re.compile(r"""['"`]([^'"`\n]+?\.md)['"`]""")

_RE_BARE    = re.compile(r"(?:^|[\s,;>(])((?:\.{1,2}/)?[A-Za-z0-9_][A-Za-z0-9_\-./]*\.md)(?=[\s,;:.)]|$)", re.MULTILINE)

def extract_link_refs(content):
    """
    Renvoie l'ensemble des références à d'autres .md trouvées dans le contenu.
    4 patterns reconnus :
      1. [[wikilink]]               (avec |alias et #ancre facultatifs)
      2. [label](path/to/file.md)   (lien Markdown standard)
      3. 'foo.md' "foo.md" `foo.md` (chemins entre guillemets/backticks)
      4. references/file.md         (chemin nu en texte courant)
    """
    refs = set()
    for m in _RE_WIKI.finditer(content):   refs.add(m.group(1).strip())
    for m in _RE_MDLINK.finditer(content):
        v = m.group(1).strip()
        if not v.lower().startswith(("http://","https://")): refs.add(v)
    for m in _RE_QUOTED.finditer(content):
        v = m.group(1).strip()
        if not v.lower().startswith(("http://","https://")): refs.add(v)
    # La regex bare exclut nativement les URLs (contexte préc. interdit / et :)
    for m in _RE_BARE.finditer(content): refs.add(m.group(1).strip())
    return refs

def resolve_ref(raw_ref, source_path, vault_paths):
    """
    Résout une référence brute en chemin réel du vault, ou None.
    Cascade :
      1. Chemin relatif au dossier du fichier source (ex: ../parent/foo.md)
      2. Chemin partiel matchant un suffixe d'un fichier du vault (ex: references/foo.md)
      3. Fuzzy match par nom de fichier (ex: foo → foo.md n'importe où)
    """
    if not raw_ref: return None
    ref = raw_ref.strip().lstrip("/")
    if not ref.lower().endswith(".md"): ref = ref + ".md"
    ref_norm = ref.replace("\\", "/")

    # 1. Relatif au dossier source
    if source_path:
        try:
            cand = (Path(source_path).parent / ref).resolve()
            cand_s = str(cand)
            if cand_s in vault_paths: return cand_s
        except Exception: pass

    # 2. Suffixe (ex: 'references/foo.md' matche '...\skills\X\references\foo.md')
    for vp in vault_paths:
        if vp.replace("\\", "/").lower().endswith("/" + ref_norm.lower()):
            return vp
        if vp.replace("\\", "/").lower().endswith(ref_norm.lower()):
            return vp

    # 3. Fuzzy par nom de fichier
    stem = Path(ref).stem.lower()
    for vp in vault_paths:
        if Path(vp).stem.lower() == stem: return vp
    return None

def extract_tags(content):
    return list({t for t in re.findall(r"(?<!\w)#([a-zA-Z0-9_\-]+)", content)})
