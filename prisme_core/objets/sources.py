"""L'objet Source : le registre des références citées (docs/decisions/0017 et 0021).

Un objet Source est **une note du vault**, pas une ligne de base : elle s'ouvre dans
Obsidian, se modifie à la main, se sauvegarde avec le reste. Sa clé normalisée vit
dans l'en-tête (`prisme_reference`) et sert au dédoublonnage.

Deux statuts :

- **citée** : la référence apparaît dans tes notes, rien n'a été lu ;
- **ingérée** : ENGRAM a importé la source correspondante, la note d'import est liée.

Le passage de l'un à l'autre est mécanique : on relit le registre ENGRAM et on y
cherche la même référence. Rien n'est deviné.
"""
import re
import time
from pathlib import Path

from .. import frontmatter, provenance
from ..index import notify_changed
from ..vault import iter_md, safe_path, snapshot, to_trash, vault_root
from . import detection

DOSSIER = "Objets/Sources"
STATUTS = ("citee", "ingeree")
LIBELLES = {"citee": "citée", "ingeree": "ingérée"}
TITRE_CITATIONS = "Citée dans"


class ObjetInvalide(ValueError):
    pass


# ── Emplacement et nommage ──────────────────────────────────────────────
def dossier():
    d = vault_root() / DOSSIER
    d.mkdir(parents=True, exist_ok=True)
    return d


def nom_fichier(cle, genre):
    """Nom lisible et stable, dérivé de la clé : deux balayages ne créent pas deux notes."""
    if genre in ("doi", "arxiv", "isbn"):
        base = cle.replace(":", "-")
    else:
        base = re.sub(r"^https?://", "", cle)
    base = re.sub(r"[^\w\-. ]", "-", base, flags=re.UNICODE)
    base = re.sub(r"-{2,}", "-", base).strip("-. ")[:80]
    return (base or "source") + ".md"


# ── Lecture ─────────────────────────────────────────────────────────────
def _lire_note(p):
    try:
        texte = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    meta = frontmatter.parse(texte)
    if str(meta.get("prisme_type") or "") != "source":
        return None
    citations = meta.get("prisme_cite_par") or []
    if isinstance(citations, str):
        citations = [citations]
    alias = meta.get("prisme_alias") or []
    if isinstance(alias, str):
        alias = [alias]
    statut = str(meta.get("prisme_statut") or "citee")
    return {
        "chemin": str(p),
        "nom": p.name,
        "id": str(meta.get("prisme_id") or ""),
        "reference": str(meta.get("prisme_reference") or ""),
        "genre": str(meta.get("prisme_genre") or "url"),
        "titre": _titre_du_corps(texte) or p.stem,
        "statut": statut if statut in STATUTS else "citee",
        "statut_libelle": LIBELLES.get(statut, statut),
        "relu": str(meta.get("prisme_relu") or "").lower() in ("true", "oui", "1"),
        "lot": str(meta.get("prisme_lot") or ""),
        "note_liee": str(meta.get("prisme_note_liee") or ""),
        "cite_par": [str(c) for c in citations],
        "alias": [str(a) for a in alias],
        "enregistre_le": str(meta.get("prisme_enregistre_le") or ""),
        "publie_le": str(meta.get("prisme_publie_le") or ""),
    }


def _titre_du_corps(texte):
    for ligne in frontmatter.strip(texte).split("\n"):
        if ligne.startswith("# "):
            return ligne[2:].strip()
    return ""


def lister(statut=None, relu=None, lot=None):
    """Tous les objets Source du vault, les plus récents d'abord."""
    out = []
    racine = vault_root() / DOSSIER
    if racine.exists():
        for p in sorted(racine.rglob("*.md")):
            obj = _lire_note(p)
            if obj is None:
                continue
            if statut and obj["statut"] != statut:
                continue
            if relu is not None and obj["relu"] != relu:
                continue
            if lot and obj["lot"] != lot:
                continue
            out.append(obj)
    out.sort(key=lambda o: o["enregistre_le"], reverse=True)
    return out


def par_cle(cle):
    """L'objet dont la clé — ou l'un des alias d'une fusion — vaut `cle`."""
    for obj in lister():
        if obj["reference"] == cle or cle in obj["alias"]:
            return obj
    return None


# ── Écriture ────────────────────────────────────────────────────────────
def _corps(titre, cle, genre, cite_par, note_liee):
    lignes = ["# %s\n" % titre, "- Référence : `%s`" % cle, "- Genre : %s" % genre]
    if note_liee:
        lignes.append("- Source ingérée : [[%s]]" % Path(note_liee).stem)
    lignes.append("")
    lignes.append("## %s\n" % TITRE_CITATIONS)
    if cite_par:
        lignes += ["- [[%s]]" % Path(c).stem for c in cite_par]
    else:
        lignes.append("_Aucune note ne la cite pour l'instant._")
    return "\n".join(lignes) + "\n"


def enregistrer(cle, genre="url", titre="", cite_par=(), lot="", relu=False,
                brut="", raison=""):
    """Crée l'objet Source, ou complète celui qui existe déjà.

    Un objet existant n'est jamais écrasé : on ajoute les notes citantes manquantes et
    on rafraîchit le statut. Le titre saisi à la main et le corps de la note sont
    respectés, sauf pour la liste des citations, que PRISME tient à jour.
    """
    if not cle:
        raise ObjetInvalide("Référence vide")
    existant = par_cle(cle)
    cite_par = sorted({str(c) for c in cite_par if str(c).strip()})
    statut, note_liee = statut_depuis_engram(cle)

    if existant:
        p = Path(existant["chemin"])
        fusion = sorted(set(existant["cite_par"]) | set(cite_par))
        champs = {"prisme_statut": statut, "prisme_note_liee": note_liee or None}
        if fusion != existant["cite_par"]:
            champs["prisme_cite_par"] = fusion
        texte = p.read_text(encoding="utf-8", errors="replace")
        nouveau = frontmatter.update(texte, champs)
        nouveau = _remplacer_citations(nouveau, fusion)
        if nouveau != texte:
            snapshot(p, force=True)
            p.write_text(nouveau, encoding="utf-8")
            notify_changed(p)
        return {**_lire_note(p), "cree": False}

    titre = (titre or "").strip() or cle
    entete = provenance.estampiller(
        "", type="source", outil="objets",
        extra={
            "prisme_reference": cle,
            "prisme_genre": genre,
            "prisme_statut": statut,
            # Booléen réel : Obsidian l'affiche comme une case à cocher.
            "prisme_relu": bool(relu),
            "prisme_lot": lot,
            "prisme_note_liee": note_liee,
            "prisme_cite_par": cite_par,
            "prisme_brut": brut,
            "prisme_raison": raison,
        })
    p = dossier() / nom_fichier(cle, genre)
    i = 1
    while p.exists():                       # collision de nom : deux clés proches
        p = dossier() / ("%s-%d.md" % (p.stem, i))
        i += 1
    p.write_text(entete + _corps(titre, cle, genre, cite_par, note_liee), encoding="utf-8")
    notify_changed(p)
    return {**_lire_note(p), "cree": True}


_BLOC_CITATIONS = re.compile(r"(^##\s+%s\s*\n)(.*?)(?=^##\s|\Z)" % re.escape(TITRE_CITATIONS),
                             re.S | re.M)


def _remplacer_citations(texte, cite_par):
    """Réécrit la seule section « Citée dans ». Le reste de la note est à toi."""
    corps = ("\n".join("- [[%s]]" % Path(c).stem for c in cite_par) + "\n\n") if cite_par \
        else "_Aucune note ne la cite pour l'instant._\n\n"
    if _BLOC_CITATIONS.search(texte):
        return _BLOC_CITATIONS.sub(lambda m: m.group(1) + corps, texte)
    return texte.rstrip() + "\n\n## %s\n\n" % TITRE_CITATIONS + corps


def marquer_relu(cle, relu=True):
    obj = par_cle(cle)
    if not obj:
        raise ObjetInvalide("Objet inconnu : %s" % cle)
    provenance.ecrire(obj["chemin"], {"prisme_relu": bool(relu)})
    return _lire_note(Path(obj["chemin"]))


def lier(cle, chemin_note):
    """Rattache une note d'import ENGRAM à la source, et passe le statut à « ingérée »."""
    obj = par_cle(cle)
    if not obj:
        raise ObjetInvalide("Objet inconnu : %s" % cle)
    p = safe_path(chemin_note)
    if not p.is_file():
        raise ObjetInvalide("Note introuvable : %s" % chemin_note)
    provenance.ecrire(obj["chemin"], {"prisme_note_liee": str(p), "prisme_statut": "ingeree"})
    return _lire_note(Path(obj["chemin"]))


def supprimer(cle, raison=""):
    """Envoie l'objet à la corbeille et mémorise le rejet (0021 : réversibilité)."""
    from . import file as filedattente
    obj = par_cle(cle)
    if not obj:
        raise ObjetInvalide("Objet inconnu : %s" % cle)
    cible = to_trash(Path(obj["chemin"]))
    filedattente.rejeter(cle, raison)
    notify_changed(obj["chemin"])
    return {"corbeille": str(cible), "objet": obj}


# ── Lien avec ENGRAM ────────────────────────────────────────────────────
def statut_depuis_engram(cle):
    """(statut, note liée) : « ingérée » si ENGRAM a importé cette même référence.

    On relit le registre ENGRAM et on cherche la clé dans le chemin, le titre et les
    notes produites. Aucune déduction : la même référence, ou rien.
    """
    try:
        from ..engram import lire_registre
        registre = lire_registre()
    except Exception:                        # noqa: BLE001 — sans ENGRAM, tout reste « citée »
        return "citee", ""
    for info in registre.values():
        temoin = " ".join([str(info.get("chemin", "")), str(info.get("titre", ""))])
        if any(r["cle"] == cle for r in detection.references(temoin)):
            notes = [f for f in info.get("notes", []) if Path(f).exists()]
            return "ingeree", (notes[0] if notes else "")
    return "citee", ""


def rafraichir_statuts():
    """Repasse sur les objets « citée » : ceux qu'ENGRAM a depuis importés changent."""
    change = 0
    for obj in lister(statut="citee"):
        statut, note = statut_depuis_engram(obj["reference"])
        if statut == "ingeree":
            provenance.ecrire(obj["chemin"], {"prisme_statut": "ingeree",
                                              "prisme_note_liee": note or None})
            change += 1
    return change


# ── Lots ────────────────────────────────────────────────────────────────
def nouveau_lot():
    return "lot-" + time.strftime("%Y%m%d-%H%M%S")


def annuler_lot(lot):
    """Retire d'un coup les objets d'un lot **encore non relus** (0021).

    Un objet que tu as relu a été validé : il n'est jamais emporté par l'annulation.
    """
    if not lot:
        raise ObjetInvalide("Lot non précisé")
    retires, gardes = [], []
    for obj in lister(lot=lot):
        if obj["relu"]:
            gardes.append(obj["nom"])
            continue
        to_trash(Path(obj["chemin"]))
        notify_changed(obj["chemin"])
        retires.append(obj["nom"])
    return {"lot": lot, "retires": retires, "conserves": gardes}


def lots():
    """Les lots connus, du plus récent au plus ancien."""
    compte = {}
    for obj in lister():
        if not obj["lot"]:
            continue
        c = compte.setdefault(obj["lot"], {"lot": obj["lot"], "total": 0, "non_relus": 0})
        c["total"] += 1
        if not obj["relu"]:
            c["non_relus"] += 1
    return sorted(compte.values(), key=lambda c: c["lot"], reverse=True)


# ── Citations ───────────────────────────────────────────────────────────
def notes_du_vault(dossier_limite=None):
    """Les notes à balayer : tout le vault sauf les objets eux-mêmes et la corbeille."""
    racine = safe_path(dossier_limite) if dossier_limite else vault_root()
    exclu = (vault_root() / DOSSIER).resolve()
    for p in iter_md(racine):
        rp = p.resolve()
        if rp == exclu or exclu in rp.parents:
            continue
        yield p
