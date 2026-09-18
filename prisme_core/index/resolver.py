"""Resolution rapide des references de liens vers les notes du vault.

Meme cascade que markdown.resolve_ref, avec des tables de correspondance au lieu
d'un parcours de tout le vault pour chaque lien :
  1. chemin relatif au dossier de la note source ;
  2. fin de chemin exacte, segment par segment (« references/foo.md ») ;
  3. nom de fichier sans extension (« foo »).
A egalite, le chemin le plus court puis l'ordre alphabetique l'emportent, pour
un resultat stable. Difference assumee avec la V1 : « note » ne resout plus vers
« manote.md » (correspondance sur une fin de nom partielle).
"""
import posixpath
from pathlib import PurePath


def _norm(p):
    return str(p).replace("\\", "/")


class LinkResolver:
    def __init__(self, paths):
        self.paths = set(paths)
        self._by_lower = {}
        self._suffix = {}
        self._stem = {}
        for p in sorted(self.paths, key=lambda x: (len(x), x)):
            n = _norm(p)
            self._by_lower.setdefault(n.lower(), p)
            parts = n.lower().split("/")
            for k in range(1, len(parts) + 1):
                self._suffix.setdefault("/".join(parts[-k:]), p)
            self._stem.setdefault(PurePath(n).stem.lower(), p)

    def resolve(self, raw_ref, source_path=None):
        if not raw_ref:
            return None
        ref = _norm(raw_ref.strip()).lstrip("/")
        if not ref:
            return None
        if not ref.lower().endswith(".md"):
            ref += ".md"
        if source_path:
            base = posixpath.dirname(_norm(source_path))
            cand = posixpath.normpath(posixpath.join(base, ref))
            hit = self._by_lower.get(cand.lower())
            if hit:
                return hit
        clean = posixpath.normpath(ref).lower()
        if not clean.startswith("../"):
            hit = self._suffix.get(clean)
            if hit:
                return hit
        return self._stem.get(PurePath(ref).stem.lower())
