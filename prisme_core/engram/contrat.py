"""Contrat d'extraction commun a toutes les sources (docs/decisions/0013).

Inspire du RAG de Studio Litteraire : avant de lire un fichier on le verifie,
on calcule son empreinte avant ET apres extraction, et on enregistre quel
extracteur l'a lu, dans quelle version et avec quelle configuration. Si le
fichier change pendant la lecture, l'import est refuse.
"""
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

TAILLE_MAX = 2 * 1024 * 1024 * 1024        # 2 Go : au-dela, un export doit etre decoupe
APERCU = 400


class SourceInvalide(Exception):
    pass


@dataclass
class Passage:
    """Un morceau de source : un echange, une section, un article."""
    texte: str
    titre: str = ""
    date: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def empreinte(self):
        return hashlib.sha256(f"{self.titre}\n{self.texte}".encode("utf-8")).hexdigest()[:16]


@dataclass
class Extraction:
    titre: str
    passages: list
    extracteur: str
    version: int
    config: str = ""
    meta: dict = field(default_factory=dict)


class Extracteur:
    """Un extracteur par format. `reconnait` decide, `extraire` produit des passages."""
    nom = "base"
    version = 1
    extensions = ()
    config = ""

    def reconnait(self, chemin, debut):
        return chemin.suffix.lower() in self.extensions

    def extraire(self, chemin, contenu):
        raise NotImplementedError

    # ── Outils communs ────────────────────────────────────────────────
    @staticmethod
    def json_charge(contenu, chemin):
        try:
            return json.loads(contenu)
        except ValueError as e:
            raise SourceInvalide(f"{chemin.name} : JSON illisible ({e})") from e

    def signature(self):
        return f"{self.nom} v{self.version}" + (f" ({self.config})" if self.config else "")


EXTRACTEURS = []


def enregistrer(classe):
    """Decorateur : ajoute une instance de l'extracteur au registre, dans l'ordre
    de declaration (le premier qui reconnait le fichier l'emporte)."""
    EXTRACTEURS.append(classe())
    return classe


def sha256_fichier(chemin, bloc=1024 * 1024):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for morceau in iter(lambda: f.read(bloc), b""):
            h.update(morceau)
    return h.hexdigest()


def verifier(chemin):
    """Controles prealables. Renvoie (chemin resolu, taille, empreinte)."""
    p = Path(chemin).expanduser()
    if not p.exists():
        raise SourceInvalide(f"Fichier introuvable : {p}")
    p = p.resolve()
    if not p.is_file():
        raise SourceInvalide(f"Ce n'est pas un fichier : {p}")
    taille = p.stat().st_size
    if taille == 0:
        raise SourceInvalide(f"Fichier vide : {p.name}")
    if taille > TAILLE_MAX:
        raise SourceInvalide(f"Fichier trop volumineux ({taille / 1e9:.1f} Go, maximum 2 Go)")
    return p, taille, sha256_fichier(p)


def candidats(chemin, debut):
    """Extracteurs qui reconnaissent ce fichier, dans l'ordre de declaration."""
    return [e for e in EXTRACTEURS if e.reconnait(chemin, debut)]


def choisir(chemin, debut):
    liste = candidats(chemin, debut)
    return liste[0] if liste else None


def lire_texte(chemin):
    """Lecture tolerante : UTF-8, puis UTF-8 avec BOM, puis page de code locale."""
    brut = chemin.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return brut.decode(enc)
        except UnicodeDecodeError:
            continue
    return brut.decode("utf-8", errors="replace")


def extraire(chemin):
    """Applique le contrat complet a un fichier. Renvoie (Extraction, infos du fichier)."""
    p, taille, avant = verifier(chemin)
    with open(p, "rb") as f:
        debut = f.read(4096)
    liste = candidats(p, debut)
    if not liste:
        raise SourceInvalide(f"Aucun extracteur pour {p.suffix or p.name} "
                             f"(formats lus : {', '.join(sorted(formats()))})")
    contenu = lire_texte(p)
    extraction, echec = None, None
    for extracteur in liste:
        # Un extracteur qui ne trouve rien laisse sa place au suivant : un JSON qui
        # n'est pas une conversation finit ainsi chez l'extracteur JSON brut.
        try:
            extraction = extracteur.extraire(p, contenu)
            if extraction.passages:
                break
        except SourceInvalide as e:
            echec = echec or e
            extraction = None
    if extraction is None or not extraction.passages:
        raise echec or SourceInvalide(f"{p.name} : aucun contenu exploitable trouve")
    apres = sha256_fichier(p)
    if apres != avant:
        raise SourceInvalide(f"{p.name} a change pendant la lecture : import annule")
    if not extraction.passages:
        raise SourceInvalide(f"{p.name} : aucun contenu exploitable trouve")
    infos = {"chemin": str(p), "nom": p.name, "taille": taille, "sha256": avant,
             "extracteur": extraction.extracteur, "version": extraction.version,
             "config": extraction.config}
    return extraction, infos


def formats():
    out = set()
    for e in EXTRACTEURS:
        out |= set(e.extensions)
    return out
