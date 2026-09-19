"""Objets E11 dans le vault, sans index privé ni dépendance supplémentaire.

Les propositions restent incomplètes tant que l'auteur ne les a pas validées.
Chaque chemin est contrôlé, y compris les symlinks rencontrés dans le registre.
"""
import re
from pathlib import Path

from .. import frontmatter, provenance
from ..index import notify_changed
from ..vault import iter_md, safe_path, snapshot, to_trash, vault_root
from . import file, types
from .sources import ObjetInvalide

DEBUT = "<!-- prisme:fiche -->"
FIN = "<!-- /prisme:fiche -->"


def _principal(chemin):
    p = safe_path(chemin)
    if p != vault_root() and vault_root() not in p.parents:
        raise PermissionError("Les objets typés appartiennent au vault principal")
    return p


def _fiche(type_objet, titre, champs):
    corps = types.gabarit(type_objet, titre, champs)
    premier, reste = corps.split("\n\n", 1)
    fiche, suite = reste.split("\n## ", 1)
    return premier + "\n\n" + DEBUT + "\n" + fiche.rstrip() + "\n" + FIN + "\n\n## " + suite


def _lire(p):
    p = _principal(p)
    meta = provenance.lire(p)
    type_objet = meta.get("prisme_type")
    if not isinstance(type_objet, str) or type_objet not in types.TYPES:
        return None
    spec = types.definition(type_objet)
    champs = {c["nom"]: meta["prisme_" + c["nom"]] for c in spec["champs"]
              if "prisme_" + c["nom"] in meta}
    champs["statut"] = meta.get("prisme_statut", spec["statuts"][0])
    if "probabilite" in champs:
        try:
            champs["probabilite"] = float(champs["probabilite"])
        except (TypeError, ValueError):
            pass  # une note éditée à la main reste visible et corrigeable
    return dict(type=type_objet, titre=meta.get("prisme_titre", p.stem),
                id=meta.get("prisme_id", ""), cle=meta.get("prisme_cle", ""),
                chemin=p.relative_to(vault_root()).as_posix(), champs=champs,
                relu=str(meta.get("prisme_relu", "false")).lower() == "true",
                origine=meta.get("prisme_origine", ""),
                enregistre_le=meta.get("prisme_enregistre_le", ""))


def lister(type_objet=None):
    if type_objet:
        types.definition(type_objet)
    # Tous les emplacements du vault principal : déplacer une note ne la fait pas disparaître.
    out = []
    for p in iter_md(vault_root()):
        try:
            obj = _lire(p)
        except (PermissionError, FileNotFoundError, ValueError):
            continue
        if obj and (not type_objet or obj["type"] == type_objet):
            out.append(obj)
    return sorted(out, key=lambda o: o["enregistre_le"], reverse=True)


def par_cle(cle):
    return next((o for o in lister() if o["cle"] == cle), None)


def _meta(type_objet, titre, champs):
    # Vider un champ facultatif retire sa propriété, sans toucher aux champs étrangers.
    return {"prisme_" + c["nom"]: champs.get(c["nom"])
            for c in types.definition(type_objet)["champs"]} | {
                "prisme_statut": champs["statut"], "prisme_titre": titre}


def creer(type_objet, titre, champs, *, origine="auteur", raison="", note="", indice="",
          cle_proposition=""):
    titre, champs = types.valider(type_objet, titre, champs)
    raison = types.texte(raison, "Raison")
    cle = types.cle_de(type_objet, titre)
    if par_cle(cle):
        raise ObjetInvalide("Un objet de ce type porte déjà ce titre ; ouvrez-le ou précisez le titre")
    if note:
        note = _principal(note).relative_to(vault_root()).as_posix()
    # Dossier et nom ne proviennent jamais d'un chemin fourni par un agent.
    dossier = _principal(vault_root() / "Objets" / types.definition(type_objet)["dossier"])
    dossier.mkdir(parents=True, exist_ok=True)
    nom = re.sub(r"[^\w -]", "-", titre).strip(" .-")[:60] or type_objet
    p = _principal(dossier / (nom + "-" + provenance.new_id() + ".md"))
    extra = {**_meta(type_objet, titre, champs), "prisme_cle": cle,
             "prisme_relu": True, "prisme_origine": origine, "prisme_raison": raison,
             "prisme_note_origine": note, "prisme_indice": indice,
             "prisme_proposition": cle_proposition, "prisme_schema": 1}
    contenu = provenance.estampiller(_fiche(type_objet, titre, champs),
                                    type=type_objet, outil="objets",
                                    genere_par=origine if origine != "auteur" else "",
                                    sources=[note] if note else [], extra=extra)
    with p.open("x", encoding="utf-8", newline="\n") as sortie:
        sortie.write(contenu)
    notify_changed(p)
    return _lire(p)


def modifier(cle, titre, champs, raison=""):
    obj = par_cle(cle)
    if not obj:
        raise ObjetInvalide("Objet inconnu")
    titre, champs = types.valider(obj["type"], titre, champs)
    raison = types.texte(raison, "Raison")
    nouvelle = types.cle_de(obj["type"], titre)
    autre = par_cle(nouvelle)
    if autre and autre["id"] != obj["id"]:
        raise ObjetInvalide("Ce titre appartient déjà à un autre objet")
    p = _principal(obj["chemin"])
    texte = p.read_text(encoding="utf-8")
    # Seul le bloc généré est remplacé. Les notes libres et champs Obsidian survivent.
    genere = _fiche(obj["type"], titre, champs)
    bloc = genere[genere.index(DEBUT):genere.index(FIN) + len(FIN)]
    texte = re.sub(re.escape(DEBUT) + r".*?" + re.escape(FIN), lambda _: bloc,
                   texte, count=1, flags=re.S)
    texte = re.sub(r"^# .*?$", lambda _: "# " + titre, texte, count=1, flags=re.M)
    meta = {**_meta(obj["type"], titre, champs), "prisme_cle": nouvelle,
            "prisme_modifie_le": provenance.horodatage(), "prisme_raison": raison or None}
    _principal(vault_root() / ".trash" / "versions")
    snapshot(p, force=True)
    p.write_text(frontmatter.update(texte, meta), encoding="utf-8")
    notify_changed(p)
    return _lire(p)


def proposer(type_objet, titre, champs, *, origine, note="", indice="", motif=""):
    titre, champs = types.valider(type_objet, titre, champs, partiel=True)
    note = types.texte(note, "Note d’origine")
    indice = types.texte(indice, "Extrait")
    motif = types.texte(motif, "Motif")
    if note:
        p = _principal(note)
        if not p.is_file() or p.suffix.lower() != ".md":
            raise ObjetInvalide("Note d'origine Markdown attendue")
        if indice and indice not in p.read_text(encoding="utf-8"):
            raise ObjetInvalide("Extrait introuvable dans la note d'origine")
        note = p.relative_to(vault_root()).as_posix()
    cle = types.cle_de(type_objet, titre)
    if par_cle(cle):
        motif = "Doublon possible : préciser le titre ou corriger l'objet existant. " + motif
    return file.ajouter(dict(cle=cle, type=type_objet, titre=titre, champs=champs,
                             origine=origine, note=note, indice=indice, motif=motif))


def accepter(cle, titre=None, champs=None, raison=""):
    entree = file.par_cle(cle)
    if not entree or entree.get("type") not in types.TYPES:
        raise ObjetInvalide("Proposition typée inconnue")
    obj = creer(entree["type"], entree["titre"] if titre is None else titre,
                entree["champs"] if champs is None else champs, origine=entree["origine"],
                raison=raison, note=entree["note"], indice=entree["indice"], cle_proposition=cle)
    file.retirer(cle)  # après écriture seulement : une validation invalide reste en file
    return {"objet": obj, "raison": raison}


def supprimer(cle, raison=""):
    obj = par_cle(cle)
    if not obj:
        raise ObjetInvalide("Objet inconnu")
    raison = types.texte(raison, "Raison")
    p = _principal(obj["chemin"])
    _principal(vault_root() / ".trash" / "versions")
    provenance.ecrire(p, {"prisme_invalide_le": provenance.horodatage(),
                         "prisme_raison_retrait": raison})
    # La corbeille elle-même ne doit pas pouvoir pointer hors des racines.
    safe_path(vault_root() / ".trash")
    cible = to_trash(p)
    file.rejeter(cle, raison)
    notify_changed(p)
    return {"objet": obj, "corbeille": str(cible)}
