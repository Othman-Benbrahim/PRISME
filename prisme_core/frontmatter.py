"""Lecture et ecriture de l'en-tete YAML des notes (frontmatter).

Sans dependance : seul le sous-ensemble YAML qu'Obsidian affiche dans son panneau
Proprietes est gere (scalaires et listes simples). Tout le reste est conserve tel
quel, ligne par ligne : PRISME ne reecrit que les cles qu'il touche, jamais le
fichier entier. Les commentaires et l'ordre des cles sont preserves.
"""
import json
import re

DELIM = "---"
_KEY = re.compile(r"^([A-Za-z0-9_][\w\-. ]*):\s?(.*)$")
_ITEM = re.compile(r"^\s*-\s+(.*)$")
_NEEDS_QUOTE = re.compile(r"^\s|\s$|^$|^[\[{>|*&!%@`#-]|: |:$|[\"']|^(true|false|null|yes|no|on|off|~)$", re.I)


def split(text):
    """Renvoie (lignes de l'en-tete sans les delimiteurs, corps, fin de ligne)."""
    nl = "\r\n" if "\r\n" in text[:2000] else "\n"
    lines = text.split(nl) if nl == "\n" else text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != DELIM:
        return [], text, nl
    for i in range(1, min(len(lines), 500)):
        if lines[i].strip() in (DELIM, "..."):
            body = nl.join(lines[i + 1:])
            return lines[1:i], body, nl
    return [], text, nl                       # en-tete jamais referme : on n'y touche pas


def _unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        if value[0] == '"':
            try:
                return json.loads(value)
            except ValueError:
                pass  # tolérer les anciens scalaires YAML non JSON
        return value[1:-1].replace('\\"', '"')
    return value


def _quote(value):
    value = "" if value is None else str(value)
    return '"%s"' % value.replace('\\', '\\\\').replace('"', '\\"') if _NEEDS_QUOTE.search(value) else value


def parse(text):
    """Dictionnaire des cles de premier niveau. Une liste devient une liste de chaines."""
    head, _body, _nl = split(text)
    data, key = {}, None
    for line in head:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _KEY.match(line)
        if m and not line.startswith((" ", "\t")):
            key = m.group(1).strip()
            raw = m.group(2).strip()
            if raw.startswith("[") and raw.endswith("]"):
                inner = raw[1:-1].strip()
                data[key] = [_unquote(x) for x in inner.split(",") if x.strip()] if inner else []
            else:
                data[key] = _unquote(raw) if raw else []     # cle nue : liste a venir
            continue
        item = _ITEM.match(line)
        if item is not None and key is not None:
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(_unquote(item.group(1)))
    return {k: v for k, v in data.items()}


def _render(key, value):
    if isinstance(value, (list, tuple)):
        return ["%s: [%s]" % (key, ", ".join(_quote(v) for v in value))]
    if isinstance(value, bool):
        return ["%s: %s" % (key, "true" if value else "false")]
    if isinstance(value, (int, float)):
        return ["%s: %s" % (key, value)]
    return ["%s: %s" % (key, _quote(value))]


def update(text, changes):
    """Ecrit les cles de `changes` dans l'en-tete (None = supprimer la cle).
    Le corps de la note n'est jamais modifie ; l'en-tete est cree s'il manque."""
    changes = {k: v for k, v in changes.items()}
    if not changes:
        return text
    head, body, nl = split(text)
    had_head = bool(head) or text.lstrip().startswith(DELIM)
    out, seen, key, skipping = [], set(), None, False
    for line in head:
        m = _KEY.match(line) if not line.startswith((" ", "\t")) else None
        if m:
            key = m.group(1).strip()
            skipping = key in changes
            if skipping:
                seen.add(key)
                if changes[key] is not None:
                    out.extend(_render(key, changes[key]))
                continue
        elif skipping and (_ITEM.match(line) or line.startswith((" ", "\t"))):
            continue                          # ligne de continuation d'une cle remplacee
        else:
            skipping = False
        out.append(line)
    for k, v in changes.items():
        if k not in seen and v is not None:
            out.extend(_render(k, v))
    if not out:
        return body if had_head else text
    return nl.join([DELIM] + out + [DELIM, ""]) + (body if had_head else text)


def strip(text):
    """Le corps de la note, sans en-tete."""
    return split(text)[1]
