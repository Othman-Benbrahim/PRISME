"""Repérage mécanique des références dans un texte (docs/decisions/0021).

La confiance repose sur des signaux vérifiables, jamais sur l'auto-évaluation d'un
modèle : ce module ne fait que reconnaître des formes (URL, DOI, identifiant arXiv,
ISBN) et les ramener à une clé normalisée. Ce qui passe ici entre directement dans le
vault ; ce qui n'est que déduit par l'IA part en file de validation.

La normalisation sert au dédoublonnage : deux notes qui citent la même page avec des
paramètres de suivi différents doivent produire la même clé.
"""
import re
from urllib.parse import parse_qsl, urlsplit, urlunsplit

# Les délimiteurs fermants sont exclus pour ne pas avaler la ponctuation d'une phrase
# ni le « ) » d'un lien markdown.
RE_URL = re.compile(r"https?://[^\s<>\"'\)\]}]+", re.I)
RE_DOI = re.compile(r"\b10\.\d{4,9}/[-._;()/:a-z0-9]+\b", re.I)
RE_ARXIV = re.compile(
    r"\barxiv[:\s/]*((?:\d{4}\.\d{4,5})(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})\b", re.I)
RE_ISBN = re.compile(r"\bISBN(?:[-\s]?1[03])?[:\s]*((?:97[89][-\s]?)?(?:\d[-\s]?){9}[\dXx])\b")

# Paramètres de campagne : ils changent d'un partage à l'autre et ne désignent rien.
PARAMS_SUIVI = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id",
    "gclid", "fbclid", "msclkid", "mc_cid", "mc_eid", "igshid", "ref", "ref_src",
    "s", "spm", "yclid", "_ga", "_gl", "si",
}
GENRES = ("url", "doi", "arxiv", "isbn")

# Un lien vers un fichier local ou un hôte sans point n'est pas une source publiable.
_HOTE_VALIDE = re.compile(r"^[a-z0-9][a-z0-9.\-]*\.[a-z]{2,}$", re.I)


def normaliser_url(url):
    """Ramène une URL à sa forme canonique, ou renvoie None si elle n'en est pas une.

    http devient https (le même document), l'hôte passe en minuscules, `www.` saute,
    les paramètres de suivi sont retirés et les autres sont triés. Le fragment est
    conservé seulement s'il ressemble à une ancre utile.
    """
    try:
        parts = urlsplit((url or "").strip().rstrip(".,;:!?»\"'"))
    except ValueError:
        return None
    hote = (parts.hostname or "").lower()
    if hote.startswith("www."):
        hote = hote[4:]
    if not _HOTE_VALIDE.match(hote):
        return None
    port = ""
    if parts.port and parts.port not in (80, 443):
        port = ":%d" % parts.port
    chemin = re.sub(r"/+", "/", parts.path or "/")
    if len(chemin) > 1:
        chemin = chemin.rstrip("/")
    gardes = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
              if k.lower() not in PARAMS_SUIVI]
    requete = "&".join("%s=%s" % (k, v) for k, v in sorted(gardes))
    return urlunsplit(("https", hote + port, chemin, requete, ""))


def normaliser_doi(ident):
    return "doi:" + re.sub(r"[.,;:)\]]+$", "", (ident or "").strip().lower())


def normaliser_arxiv(ident):
    """Les versions (v1, v2) désignent le même travail : elles ne font pas deux sources."""
    return "arxiv:" + re.sub(r"v\d+$", "", (ident or "").strip().lower())


def normaliser_isbn(ident):
    return "isbn:" + re.sub(r"[^0-9Xx]", "", (ident or "")).upper()


def _titre_probable(cle, genre, brut):
    """Un nom lisible tant que personne n'a ouvert la référence."""
    if genre == "url":
        parts = urlsplit(cle)
        dernier = [s for s in (parts.path or "").split("/") if s]
        if dernier:
            mot = re.sub(r"\.(html?|php|aspx?|pdf)$", "", dernier[-1], flags=re.I)
            mot = re.sub(r"[-_+]+", " ", mot).strip()
            if len(mot) > 2 and not mot.isdigit():
                return "%s — %s" % (parts.hostname, mot[:80])
        return parts.hostname or cle
    # Un identifiant repéré dans une URL : la clé est plus parlante que l'adresse.
    if brut.strip().lower().startswith("http"):
        return cle
    return brut.strip()


def references(texte):
    """Toutes les références d'un texte : [{cle, brut, genre, titre, position}].

    Une même référence citée deux fois ne ressort qu'une fois, à sa première position.
    Les identifiants arXiv et DOI contenus dans une URL déjà repérée ne sont pas
    comptés une seconde fois : la page et l'identifiant désignent le même travail.
    """
    texte = texte or ""
    vues, out = {}, []

    def ajouter(cle, brut, genre, position):
        if not cle or cle in vues:
            return
        vues[cle] = True
        out.append({"cle": cle, "brut": brut.strip(), "genre": genre,
                    "titre": _titre_probable(cle, genre, brut), "position": position})

    spans_url = []
    for m in RE_URL.finditer(texte):
        spans_url.append(m.span())
        brut = m.group(0)
        # Une URL arXiv ou doi.org vaut mieux comme identifiant que comme adresse :
        # le même article partagé par deux chemins doit donner une seule source.
        ma = RE_ARXIV.search(brut) or re.search(r"arxiv\.org/(?:abs|pdf)/([^\s?#]+)", brut, re.I)
        md = RE_DOI.search(brut)
        if ma:
            ident = ma.group(1)
            ajouter(normaliser_arxiv(re.sub(r"\.pdf$", "", ident, flags=re.I)), brut, "arxiv", m.start())
        elif md and "doi.org" in brut.lower():
            ajouter(normaliser_doi(md.group(0)), brut, "doi", m.start())
        else:
            ajouter(normaliser_url(brut), brut, "url", m.start())

    def hors_url(position):
        return not any(a <= position < b for a, b in spans_url)

    for m in RE_DOI.finditer(texte):
        if hors_url(m.start()):
            ajouter(normaliser_doi(m.group(0)), m.group(0), "doi", m.start())
    for m in RE_ARXIV.finditer(texte):
        if hors_url(m.start()):
            ajouter(normaliser_arxiv(m.group(1)), m.group(0), "arxiv", m.start())
    for m in RE_ISBN.finditer(texte):
        if hors_url(m.start()):
            cle = normaliser_isbn(m.group(1))
            if len(cle) - 5 in (10, 13):
                ajouter(cle, m.group(0), "isbn", m.start())

    out.sort(key=lambda r: r["position"])
    return out


def cle_de(brut):
    """Clé normalisée d'une référence donnée à la main, ou None si elle n'en est pas une."""
    trouvees = references(brut or "")
    return trouvees[0]["cle"] if trouvees else None
