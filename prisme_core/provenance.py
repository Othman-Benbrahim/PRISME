"""Provenance des notes : identifiants, horloges, origine (docs/decisions/0012 et 0022).

Regles appliquees :
- une note ecrite a la main ne recoit un identifiant que lorsque quelque chose y
  fait reference (une synthese la cite, par exemple) ;
- une note produite par une machine en recoit un des sa creation, avec sa source,
  l'outil et le modele qui l'ont produite ;
- horloge d'enregistrement active (prisme_enregistre_le / prisme_invalide_le) ;
- horloge du monde activee explicitement par le plugin de calibration (prisme_valide_du / prisme_valide_au),
  chaque date ayant un champ d'etat compagnon : date | inconnue | ouverte.
Seul l'en-tete est ecrit : le corps d'une note n'est jamais modifie ici.
"""
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import frontmatter
from .vault import safe_path, snapshot

PREFIX = "prisme_"
ETATS = ("date", "inconnue", "ouverte")

# Champs geres. Les champs "reserves" ne sont ecrits que si on les fournit.
CHAMPS = {
    "prisme_id": "identifiant stable de la note",
    "prisme_type": "note | synthese | import | source | reponse | decision | hypothese | prediction | entite | tache",
    "prisme_enregistre_le": "date d'entree dans PRISME",
    "prisme_invalide_le": "date de retrait (vide tant que la note est valable)",
    "prisme_outil": "ce qui a produit la note (plugin, action de l'editeur)",
    "prisme_genere_par": "modele et service utilises",
    "prisme_preset": "preset de prompt utilise",
    "prisme_sources": "identifiants ou chemins des notes et sources utilisees",
    "prisme_parent": "note dont celle-ci derive",
    "prisme_publie_le": "date de publication de la source (metadonnee)",
    "prisme_valide_du": "debut de validite dans le monde",
    "prisme_valide_au": "fin de validite dans le monde",
    "prisme_valide_du_etat": "date | inconnue | ouverte",
    "prisme_valide_au_etat": "date | inconnue | ouverte",
}
RESERVES = ("prisme_valide_du", "prisme_valide_au", "prisme_valide_du_etat", "prisme_valide_au_etat")


def new_id():
    """Identifiant court, stable, sans ambiguite visuelle."""
    return uuid.uuid4().hex[:12]


def horodatage():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S")


def lire(path):
    """En-tete d'une note : {} si elle n'en a pas ou si elle est illisible."""
    try:
        return frontmatter.parse(Path(path).read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return {}


def ecrire(path, champs):
    """Ecrit des cles d'en-tete dans une note existante, apres instantane."""
    p = Path(path)
    texte = p.read_text(encoding="utf-8", errors="replace")
    nouveau = frontmatter.update(texte, champs)
    if nouveau == texte:
        return False
    snapshot(p, force=True)
    p.write_text(nouveau, encoding="utf-8")
    from .index import notify_changed        # import tardif : l'index lit le frontmatter
    notify_changed(p)
    return True


def assurer_id(path):
    """Pose un identifiant sur une note qui n'en a pas encore. Renvoie l'identifiant.
    C'est le seul cas ou PRISME modifie une note ecrite a la main, et uniquement
    quand quelque chose y fait reference."""
    p = safe_path(path)
    if not p.is_file():
        return None
    meta = lire(p)
    ident = str(meta.get("prisme_id") or "").strip()
    if ident:
        return ident
    ident = new_id()
    ecrire(p, {"prisme_id": ident})
    return ident


def estampiller(contenu, *, type="note", outil="", genere_par="", preset="",
                sources=(), parent="", extra=None):
    """Ajoute l'en-tete de provenance a une note produite par une machine."""
    champs = {
        "prisme_id": new_id(),
        "prisme_type": type,
        "prisme_enregistre_le": horodatage(),
    }
    if outil:
        champs["prisme_outil"] = outil
    if genere_par:
        champs["prisme_genere_par"] = genere_par
    if preset:
        champs["prisme_preset"] = preset
    if sources:
        champs["prisme_sources"] = list(sources)
    if parent:
        champs["prisme_parent"] = parent
    for cle, valeur in (extra or {}).items():
        if cle.startswith(PREFIX) and valeur not in (None, "", []):
            champs[cle] = valeur
    existant = frontmatter.parse(contenu)
    if existant.get("prisme_id"):
        return contenu                        # deja estampillee : on ne touche a rien
    return frontmatter.update(contenu, champs)


def decrire_modele(cfg):
    """« modele (service) », pour le champ prisme_genere_par."""
    modele = (cfg.get("model") or "").strip()
    base = (cfg.get("base_url") or "").strip()
    hote = ""
    if "://" in base:
        hote = base.split("://", 1)[1].split("/", 1)[0]
    return f"{modele} ({hote})" if modele and hote else modele or hote


def sources_vers_ids(chemins):
    """Pose un identifiant sur chaque note citee et renvoie ses identifiants.
    Un chemin hors du vault ou introuvable est conserve tel quel (URL, fichier externe)."""
    ids = []
    for brut in chemins or ():
        brut = str(brut).strip()
        if not brut:
            continue
        if "://" in brut:
            ids.append(brut)
            continue
        try:
            ident = assurer_id(brut)
        except (PermissionError, OSError):
            ident = None
        ids.append(ident or brut)
    return ids


# Champs qu'on peut renseigner a la main depuis la fiche de provenance.
MODIFIABLES = ("prisme_type", "prisme_outil", "prisme_genere_par", "prisme_preset",
               "prisme_enregistre_le", "prisme_invalide_le", "prisme_publie_le",
               "prisme_parent", "prisme_valide_du", "prisme_valide_au",
               "prisme_valide_du_etat", "prisme_valide_au_etat")
TYPES = ("note", "source", "synthese", "reponse", "import",
         "decision", "hypothese", "prediction", "entite", "tache")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?$")


class ChampInvalide(ValueError):
    pass


def valider(champs):
    """Verifie et normalise les champs saisis a la main. Leve ChampInvalide."""
    propres = {}
    for cle, valeur in (champs or {}).items():
        cle = str(cle).strip()
        if cle not in MODIFIABLES:
            raise ChampInvalide(f"Champ non modifiable : {cle}")
        if isinstance(valeur, list):
            propres[cle] = [str(v).strip() for v in valeur if str(v).strip()] or None
            continue
        valeur = "" if valeur is None else str(valeur).strip()
        if not valeur:
            propres[cle] = None                       # vide = on retire la cle
            continue
        if cle.endswith("_etat") and valeur not in ETATS:
            raise ChampInvalide(f"{cle} doit valoir : {', '.join(ETATS)}")
        if cle in ("prisme_enregistre_le", "prisme_invalide_le", "prisme_publie_le",
                   "prisme_valide_du", "prisme_valide_au") and not _DATE.match(valeur):
            raise ChampInvalide(f"{cle} : date attendue au format AAAA-MM-JJ (heure facultative)")
        if len(valeur) > 500:
            raise ChampInvalide(f"{cle} : valeur trop longue")
        propres[cle] = valeur
    # Une date renseignee implique l'etat « date » ; une date absente avec un etat
    # « date » n'a pas de sens (docs/decisions/0022).
    for champ in ("prisme_valide_du", "prisme_valide_au"):
        etat = champ + "_etat"
        if propres.get(champ) and propres.get(etat) in (None, ""):
            propres[etat] = "date"
        if propres.get(etat) == "date" and not propres.get(champ):
            raise ChampInvalide(f"{etat} vaut « date » mais {champ} est vide")
    return propres


def appliquer(path, champs, sources=None):
    """Ecrit une provenance saisie a la main. Pose un identifiant si la note n'en a pas,
    et un identifiant sur chaque note citee. Renvoie le nouveau contenu."""
    p = safe_path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    propres = valider(champs)
    if sources is not None:
        refs = sources_vers_ids(sources)
        propres["prisme_sources"] = refs or None
    if not lire(p).get("prisme_id"):
        propres["prisme_id"] = new_id()
    ecrire(p, propres)
    return p.read_text(encoding="utf-8", errors="replace")


def duree_depuis(ts):
    try:
        return round(time.time() - datetime.fromisoformat(ts).timestamp())
    except (TypeError, ValueError):
        return None
