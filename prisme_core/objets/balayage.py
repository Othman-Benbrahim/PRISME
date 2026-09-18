"""Deux chemins d'entrée pour les objets Source (docs/decisions/0017 et 0021).

1. **Balayage mécanique** — les références reconnaissables (URL, DOI, arXiv, ISBN)
   entrent directement dans le vault, non relues, sous un identifiant de lot qui
   permet de tout annuler d'un coup.
2. **Proposition de l'IA** — ce que le modèle croit reconnaître sans forme vérifiable
   part en file de validation. Chaque proposition doit citer un extrait littéral de
   la note : si cet extrait ne s'y trouve pas, elle est écartée sans t'être montrée.

Accepter, corriger, fusionner ou rejeter accepte une raison facultative, conservée et
relue avant toute nouvelle proposition : un refus ponctuel ne devient pas une règle.
"""
import json
import re
import time

from ..config import rd_cfg
from ..providers import _ai_call, needs_key
from ..vault import vault_root
from . import detection, file, sources

MAX_NOTES_IA = 12          # au-delà, l'appel coûte cher et la file devient ingérable
MAX_CAR_IA = 6000
MIN_CAR_IA = 120           # en deçà, une note est un brouillon : l'appel serait gaspillé

CONSIGNE = """Tu repères des références bibliographiques dans une note.

Ne signale QUE les références dépourvues d'URL, de DOI, d'identifiant arXiv ou
d'ISBN : celles-là sont déjà repérées automatiquement. Cherche les mentions en
clair — « le rapport X de l'organisme Y (2024) », « l'article de Z paru dans W ».

Réponds uniquement par un tableau JSON, sans commentaire :
[{"titre": "...", "indice": "extrait EXACT et littéral de la note, 5 à 15 mots",
  "motif": "pourquoi c'est une source"}]

L'extrait doit être copié caractère pour caractère depuis la note. Tableau vide si
tu n'en trouves aucune."""


def _chemin_relatif(p):
    """Chemin d'une note dans le vault, toujours en barres obliques.

    Sur Windows, `relative_to` rend « sous\\Notes.md ». Ce chemin finit dans
    `prisme_cite_par` et dans les liens `[[…]]` : il doit s'écrire comme le reste du
    vault, sinon un vault déplacé d'une machine à l'autre ne se relit plus pareil.
    """
    try:
        return p.relative_to(vault_root()).as_posix()
    except ValueError:
        return p.as_posix()


# ── 1. Entrée directe ───────────────────────────────────────────────────
def balayer(dossier=None, lot=None, limite=None):
    """Balaie les notes et crée les objets Source des références repérées mécaniquement.

    Renvoie un rapport avec l'identifiant de lot : « annuler ce lot » le défait, tant
    que les objets n'ont pas été relus.
    """
    lot = lot or sources.nouveau_lot()
    par_cle = {}
    lues = 0
    for p in sources.notes_du_vault(dossier):
        lues += 1
        if limite and lues > limite:
            break
        try:
            texte = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        chemin = _chemin_relatif(p)
        for ref in detection.references(texte):
            entree = par_cle.setdefault(ref["cle"], {**ref, "cite_par": []})
            if chemin not in entree["cite_par"]:
                entree["cite_par"].append(chemin)

    rejetes = file.rejets()
    crees, completes, ignores = [], [], []
    for cle, ref in par_cle.items():
        if cle in rejetes:                    # un refus mémorisé ne revient pas tout seul
            ignores.append(cle)
            continue
        objet = sources.enregistrer(cle, genre=ref["genre"], titre=ref["titre"],
                                    cite_par=ref["cite_par"], lot=lot, relu=False,
                                    brut=ref["brut"])
        (crees if objet.get("cree") else completes).append(objet)
    return {"lot": lot, "notes_lues": lues, "references": len(par_cle),
            "crees": crees, "completes": completes, "ignores": ignores,
            "termine_le": time.strftime("%Y-%m-%dT%H:%M:%S")}


# ── 2. Propositions de l'IA ─────────────────────────────────────────────
def _json_du_modele(texte):
    """Récupère le tableau JSON même si le modèle l'a enrobé de texte ou de balises."""
    texte = re.sub(r"^```(?:json)?|```$", "", (texte or "").strip(), flags=re.M).strip()
    debut, fin = texte.find("["), texte.rfind("]")
    if debut < 0 or fin <= debut:
        return []
    try:
        data = json.loads(texte[debut:fin + 1])
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def _normaliser_espaces(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def proposer_par_ia(dossier=None, limite=MAX_NOTES_IA):
    """Fait lire des notes par le modèle et dépose ses trouvailles en file.

    Aucune proposition n'entre dans le vault : l'IA propose, tu valides (0017).
    """
    cfg = rd_cfg()
    if needs_key(cfg):
        return {"error": "Clé API manquante — configurez-la dans Paramètres."}

    connues = {o["reference"] for o in sources.lister()}
    refus = file.raisons_connues()
    rappel = ""
    if refus:
        rappel = "\n\nRefus déjà exprimés, à ne pas reproposer :\n" + "\n".join(
            "- %s : %s" % (r["titre"] or r["cle"], r["raison"]) for r in refus)

    deposees, examinees, ecartees = [], 0, 0
    for p in sources.notes_du_vault(dossier):
        if examinees >= limite:
            break
        try:
            texte = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(texte.strip()) < MIN_CAR_IA:
            continue
        examinees += 1
        chemin = _chemin_relatif(p)
        contenu, erreur = _ai_call(
            cfg,
            [{"role": "system", "content": CONSIGNE + rappel},
             {"role": "user", "content": "Note « %s » :\n\n%s" % (chemin, texte[:MAX_CAR_IA])}],
            max_tokens=900, temp=0.1, timeout=90)
        if erreur:
            return {"error": erreur, "deposees": deposees, "notes_examinees": examinees}

        temoin = _normaliser_espaces(texte)
        for prop in _json_du_modele(contenu):
            if not isinstance(prop, dict):
                continue
            titre = str(prop.get("titre") or "").strip()
            indice = str(prop.get("indice") or "").strip()
            # Garde-fou : sans extrait littéral retrouvé dans la note, la proposition
            # est une invention du modèle et n'a rien à faire dans la file.
            if not titre or not indice or _normaliser_espaces(indice) not in temoin:
                ecartees += 1
                continue
            cle = "texte:" + _normaliser_espaces(titre)[:120]
            if cle in connues:
                continue
            entree = file.ajouter({"cle": cle, "brut": titre, "genre": "texte",
                                   "titre": titre, "origine": "ia", "note": chemin,
                                   "indice": indice, "motif": str(prop.get("motif") or "")})
            if entree:
                deposees.append(entree)
    return {"deposees": deposees, "notes_examinees": examinees, "ecartees": ecartees,
            "en_file": len(file.lister())}


# ── 3. Décisions sur la file ────────────────────────────────────────────
def accepter(cle, titre=None, reference=None, raison=""):
    """Fait entrer une proposition dans le vault, éventuellement corrigée.

    `reference` permet de coller l'URL ou le DOI que l'IA n'avait pas : la référence
    redevient alors vérifiable et l'objet prend sa vraie clé.
    """
    entree = file.par_cle(cle)
    if not entree:
        raise sources.ObjetInvalide("Proposition inconnue : %s" % cle)
    genre, finale = entree["genre"], cle
    if reference:
        verifiee = detection.cle_de(reference)
        if not verifiee:
            raise sources.ObjetInvalide(
                "Référence non reconnue : attendu une URL, un DOI, un identifiant arXiv ou un ISBN")
        finale = verifiee
        genre = detection.references(reference)[0]["genre"]
    objet = sources.enregistrer(finale, genre=genre,
                                titre=(titre or entree["titre"]).strip(),
                                cite_par=[entree["note"]] if entree.get("note") else [],
                                lot=entree.get("origine", "file"), relu=True,
                                brut=entree.get("brut", ""), raison=raison)
    file.retirer(cle)
    return {"objet": objet, "raison": raison}


def rejeter_proposition(cle, raison=""):
    if not file.par_cle(cle):
        raise sources.ObjetInvalide("Proposition inconnue : %s" % cle)
    return file.rejeter(cle, raison)


def fusionner(cle_gardee, cle_absorbee, raison=""):
    """Réunit deux objets en un seul. La fusion est réversible (révision de 0017).

    La clé absorbée devient un alias de l'objet gardé : une note qui la citait
    continue de retrouver le bon objet. Le journal `prisme_fusions` garde de quoi
    défaire l'opération.
    """
    from pathlib import Path

    from .. import frontmatter, provenance
    from ..index import notify_changed
    from ..vault import snapshot, to_trash

    if cle_gardee == cle_absorbee:
        raise sources.ObjetInvalide("Les deux références sont identiques")
    garde = sources.par_cle(cle_gardee)
    absorbe = sources.par_cle(cle_absorbee)
    if not garde:
        raise sources.ObjetInvalide("Objet inconnu : %s" % cle_gardee)
    if not absorbe:
        # L'absorbée peut n'être qu'une proposition en file : on la retire aussi.
        if file.par_cle(cle_absorbee):
            file.retirer(cle_absorbee)
            alias = sorted(set(garde["alias"]) | {cle_absorbee})
            provenance.ecrire(garde["chemin"], {"prisme_alias": alias})
            return {"garde": sources.par_cle(cle_gardee), "absorbe": None, "raison": raison}
        raise sources.ObjetInvalide("Objet inconnu : %s" % cle_absorbee)

    p = Path(garde["chemin"])
    texte = p.read_text(encoding="utf-8", errors="replace")
    meta = frontmatter.parse(texte)
    journal = meta.get("prisme_fusions") or []
    if isinstance(journal, str):
        journal = [journal]
    journal.append("%s|%s|%s|%s" % (cle_absorbee, absorbe["nom"],
                                    time.strftime("%Y-%m-%dT%H:%M:%S"), raison))
    citations = sorted(set(garde["cite_par"]) | set(absorbe["cite_par"]))
    alias = sorted(set(garde["alias"]) | set(absorbe["alias"]) | {cle_absorbee})
    nouveau = frontmatter.update(texte, {
        "prisme_cite_par": citations, "prisme_alias": alias, "prisme_fusions": journal})
    nouveau = sources._remplacer_citations(nouveau, citations)
    snapshot(p, force=True)
    p.write_text(nouveau, encoding="utf-8")
    corbeille = to_trash(Path(absorbe["chemin"]))
    notify_changed(p, absorbe["chemin"])
    return {"garde": sources.par_cle(cle_gardee), "absorbe": absorbe,
            "corbeille": str(corbeille), "raison": raison}


def defusionner(cle_gardee, cle_absorbee):
    """Annule une fusion : l'alias saute et l'objet absorbé est recréé, non relu."""
    from pathlib import Path

    from .. import frontmatter, provenance

    garde = sources.par_cle(cle_gardee)
    if not garde:
        raise sources.ObjetInvalide("Objet inconnu : %s" % cle_gardee)
    if cle_absorbee not in garde["alias"]:
        raise sources.ObjetInvalide("Aucune fusion enregistrée pour %s" % cle_absorbee)
    meta = frontmatter.parse(Path(garde["chemin"]).read_text(encoding="utf-8", errors="replace"))
    journal = meta.get("prisme_fusions") or []
    if isinstance(journal, str):
        journal = [journal]
    reste = [j for j in journal if not str(j).startswith(cle_absorbee + "|")]
    provenance.ecrire(garde["chemin"], {
        "prisme_alias": [a for a in garde["alias"] if a != cle_absorbee] or None,
        "prisme_fusions": reste or None})
    genre = (detection.references(cle_absorbee) or [{"genre": "url"}])[0]["genre"]
    recree = sources.enregistrer(cle_absorbee, genre=genre, titre=cle_absorbee, relu=False)
    return {"garde": sources.par_cle(cle_gardee), "recree": recree}


# ── 4. Ce qu'une note cite ──────────────────────────────────────────────
def objets_lies_a(chemin_note):
    """Les objets Source cités par une note, avec le marqueur des non relus (0021)."""
    from ..vault import safe_path

    p = safe_path(chemin_note)
    if not p.is_file():
        return []
    # Une note d'objet cite sa propre référence : l'afficher n'apprendrait rien.
    racine_objets = (vault_root() / sources.DOSSIER).resolve()
    if racine_objets in p.resolve().parents:
        return []
    texte = p.read_text(encoding="utf-8", errors="replace")
    cles = {r["cle"] for r in detection.references(texte)}
    relatif = _chemin_relatif(p)
    out = []
    for obj in sources.lister():
        if obj["reference"] in cles or cles & set(obj["alias"]) or relatif in obj["cite_par"]:
            out.append({**obj, "non_relu": not obj["relu"]})
    return out
