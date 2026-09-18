"""ENGRAM : ingestion idempotente d'une source dans le vault (docs/decisions/0013 a 0016).

Reimporter la meme source ne cree pas de doublon : le fichier est compare par
empreinte (inchange, modifie), et a l'interieur d'une source modifiee seuls les
passages qui ont bouge sont reecrits. Les passages disparus sont archives, pas
supprimes.
"""
import json
import shutil
import time
from pathlib import Path

from .. import provenance
from ..config import rd_cfg
from ..index import notify_changed
from ..vault import safe_path, snapshot, vault_root
from . import contrat, identite, notes
from .contrat import SourceInvalide          # noqa: F401 (reexporte)

DOSSIER_SOURCES = "_sources"
DOSSIER_NOTES = "Sources"
REGISTRE = "engram.json"


# ── Registre (profil) ───────────────────────────────────────────────────
def _fichier_registre():
    from ..paths import DATA_DIR
    d = DATA_DIR / "engram"
    d.mkdir(parents=True, exist_ok=True)
    return d / REGISTRE


def lire_registre():
    try:
        return json.loads(_fichier_registre().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def ecrire_registre(data):
    _fichier_registre().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _cle(sha256):
    return sha256[:16]


# ── Import ──────────────────────────────────────────────────────────────
def inspecter(chemin):
    """Ce qu'on sait d'une source avant de l'importer, sans rien ecrire."""
    p, taille, sha = contrat.verifier(chemin)
    with open(p, "rb") as f:
        debut = f.read(4096)
    extracteur = contrat.choisir(p, debut)
    registre = lire_registre()
    connue = registre.get(_cle(sha))
    precedente = next((v for v in registre.values() if v.get("chemin") == str(p)), None)
    return {
        "chemin": str(p), "nom": p.name, "taille": taille, "sha256": sha,
        "extracteur": extracteur.signature() if extracteur else None,
        "formats_connus": sorted(contrat.formats()),
        "etat": "inchangee" if connue else ("modifiee" if precedente else "nouvelle"),
        "precedent": precedente,
    }


def _dossier_notes():
    d = vault_root() / DOSSIER_NOTES
    d.mkdir(parents=True, exist_ok=True)
    return d


def _copier_source(p, sha):
    dest_dir = vault_root() / DOSSIER_SOURCES
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{sha[:12]}-{p.name}"
    if not dest.exists():
        shutil.copy2(p, dest)
    return dest


def importer(chemin, mode="reference", dossier=None, seuil=notes.SEUIL_PARTIE, forcer=False):
    """Importe (ou reimporte) une source. mode : « reference » ou « copie »."""
    if mode not in ("reference", "copie"):
        raise SourceInvalide("Mode inconnu : attendu « reference » ou « copie »")
    extraction, infos = contrat.extraire(chemin)
    sha, source = infos["sha256"], Path(infos["chemin"])
    registre = lire_registre()
    cle = _cle(sha)
    ancienne = registre.get(cle)
    precedente = next((v for v in registre.values() if v.get("chemin") == str(source)), None)

    if ancienne and not forcer and all(Path(f).exists() for f in ancienne.get("notes", [])):
        return {"etat": "inchangee", "message": "Source déjà importée, à l'identique.",
                "notes": ancienne["notes"], "comptes": {}, "source": str(source)}

    # Passages deja ecrits : on repart de ce que le vault contient (les identifiants
    # vivent dans les notes, pas dans le registre).
    anciens, archives = [], []
    for f in (precedente or {}).get("notes", []):
        p = Path(f)
        if p.exists():
            contenu = p.read_text(encoding="utf-8", errors="replace")
            anciens.extend(notes.passages_existants(contenu))
            archives.extend(notes.archives_existantes(contenu))

    attributions, retires = identite.reconcilier(anciens, extraction.passages)
    date = time.strftime("%Y-%m-%d %H:%M")
    archives += [notes.rendre_archive(r, date, sha) for r in retires]

    interne = _copier_source(source, sha) if mode == "copie" else None
    base = notes.slug(extraction.titre or source.stem)
    dossier_cible = safe_path(dossier) if dossier else _dossier_notes()
    dossier_cible.mkdir(parents=True, exist_ok=True)

    parties = notes.repartir(attributions, seuil)
    fichiers = [dossier_cible / n for n in notes.noms_parties(base, len(parties))]
    sommaire_path = None
    if len(parties) > 1:
        sommaire_path = dossier_cible / f"{base}.md"

    ecrits = []
    for i, (fichier, lot) in enumerate(zip(fichiers, parties), 1):
        entete = provenance.estampiller(
            "", type="import", outil="engram",
            genere_par="", preset="",
            sources=[str(source)] if mode == "reference" else [str(interne)],
            extra={
                "prisme_source_sha256": sha,
                "prisme_source_mode": mode,
                "prisme_source_chemin": str(source),
                "prisme_source_extracteur": f"{infos['extracteur']} v{infos['version']}"
                                            + (f" ({infos['config']})" if infos["config"] else ""),
                "prisme_source_partie": f"{i}/{len(parties)}" if len(parties) > 1 else "",
                "prisme_source_cle": cle,
            })
        titre = extraction.titre if len(parties) == 1 else f"{extraction.titre} — partie {i}"
        contenu = notes.composer(titre, entete, lot,
                                 archives if i == len(parties) else [])
        if fichier.exists():
            snapshot(fichier, force=True)
        fichier.write_text(contenu, encoding="utf-8")
        ecrits.append(str(fichier))

    if sommaire_path is not None:
        entete = provenance.estampiller(
            "", type="import", outil="engram", sources=[str(source)],
            extra={"prisme_source_sha256": sha, "prisme_source_cle": cle,
                   "prisme_source_mode": mode, "prisme_source_chemin": str(source)})
        sommaire = notes.sommaire_markdown(base, [Path(f).name for f in ecrits],
                                           [len(l) for l in parties])
        if sommaire_path.exists():
            snapshot(sommaire_path, force=True)
        sommaire_path.write_text(entete + f"# {extraction.titre}\n\n" + sommaire, encoding="utf-8")
        ecrits.insert(0, str(sommaire_path))

    # Les notes d'un import precedent qui ne servent plus (source raccourcie)
    obsoletes = [f for f in (precedente or {}).get("notes", []) if f not in ecrits and Path(f).exists()]
    for f in obsoletes:
        snapshot(Path(f), force=True)

    for f in ecrits:
        notify_changed(f)

    if precedente and precedente is not ancienne:
        registre = {k: v for k, v in registre.items() if v.get("chemin") != str(source)}
    registre[cle] = {
        "chemin": str(source), "sha256": sha, "mode": mode,
        "copie": str(interne) if interne else "",
        "extracteur": infos["extracteur"], "version": infos["version"],
        "titre": extraction.titre, "notes": ecrits, "passages": len(attributions),
        "importee_le": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    ecrire_registre(registre)

    comptes = identite.comptes(attributions, retires)
    return {"etat": "modifiee" if precedente else "nouvelle", "notes": ecrits, "comptes": comptes,
            "source": str(source), "titre": extraction.titre, "parties": len(parties),
            "obsoletes": obsoletes, "extracteur": f"{infos['extracteur']} v{infos['version']}",
            "cle": cle}


# ── Controle ────────────────────────────────────────────────────────────
def controler():
    """Etat des sources connues : disparue, modifiee, ou intacte."""
    out = []
    for cle, info in sorted(lire_registre().items(), key=lambda kv: kv[1].get("importee_le", "")):
        p = Path(info["chemin"])
        if not p.exists():
            etat = "copie conservée" if info.get("copie") and Path(info["copie"]).exists() else "disparue"
        else:
            etat = "intacte" if contrat.sha256_fichier(p) == info["sha256"] else "modifiée"
        out.append({**info, "cle": cle, "etat": etat,
                    "notes_presentes": [f for f in info.get("notes", []) if Path(f).exists()]})
    return out


def oublier(cle):
    """Retire une source du registre. Les notes et les copies restent dans le vault."""
    registre = lire_registre()
    if cle not in registre:
        raise SourceInvalide(f"Source inconnue : {cle}")
    info = registre.pop(cle)
    ecrire_registre(registre)
    return info


def seuil_configure():
    try:
        return int(rd_cfg().get("engram_seuil_partie") or notes.SEUIL_PARTIE)
    except (TypeError, ValueError):
        return notes.SEUIL_PARTIE
