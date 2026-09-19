"""Surface `/api/v1/` : ce qu'un agent extérieur peut faire (docs/decisions/0018).

Lecture et proposition par défaut. Une proposition atterrit dans la file de
validation d'E5 sous l'étiquette de l'agent — le plafond par origine devient donc un
plafond par clé. L'écriture directe demande le droit `ecriture`, accordé clé par clé.

L'authentification est faite en amont par `agents.garde`, branchée dans la garde
globale : une route de ce module ne s'exécute jamais sans `g.agent`.
"""
from pathlib import Path

from flask import Blueprint, g, jsonify, request

from .. import provenance
from ..agents.garde import exige
from ..agents import cles as trousseau
from ..index import fresh_index, notify_changed
from ..index import search as query
from ..objets import detection, sources
from ..objets import file as filedattente
from ..vault import iter_md, safe_path, snapshot, vault_root

bp = Blueprint("agent_api", __name__)
PREFIX = "/api/v1"
MAX_NOTES = 500
MAX_TAILLE = 400_000          # une note plus grosse n'a pas a transiter par l'API


def _relatif(p):
    try:
        return Path(p).relative_to(vault_root()).as_posix()
    except ValueError:
        return Path(p).as_posix()


# ── Découverte ──────────────────────────────────────────────────────────
@bp.route(PREFIX + "/", methods=["GET"])
@bp.route(PREFIX + "/ping", methods=["GET"])
@exige("lecture")
def ping():
    """Qui suis-je, que puis-je faire. Un agent commence par là."""
    return jsonify({
        "prisme": True,
        "agent": g.agent["nom"],
        "droits": g.agent["droits"],
        "routes": {
            "GET /api/v1/notes": "lister les notes du vault (lecture)",
            "GET /api/v1/note?path=": "lire une note (lecture)",
            "GET /api/v1/recherche?q=": "chercher dans le vault (lecture)",
            "GET /api/v1/arbre?q=": "chercher en suivant les liens : carte des relations "
                                    "et notes retenues, sans appeler de modèle (lecture)",
            "GET /api/v1/objets": "lister les objets Source (lecture)",
            "POST /api/v1/proposer": "déposer une référence dans la file de validation (proposition)",
            "POST /api/v1/note": "écrire une note (ecriture, accordé au cas par cas)",
        },
    })


# ── Lecture ─────────────────────────────────────────────────────────────
@bp.route(PREFIX + "/notes", methods=["GET"])
@exige("lecture")
def notes():
    racine = vault_root()
    out = []
    for p in iter_md(racine):
        out.append({"chemin": _relatif(p), "taille": p.stat().st_size})
        if len(out) >= MAX_NOTES:
            break
    return jsonify({"notes": out, "total": len(out), "plafond": MAX_NOTES})


@bp.route(PREFIX + "/note", methods=["GET"])
@exige("lecture")
def lire_note():
    try:
        p = safe_path(request.args.get("path", ""))
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    if not p.is_file() or p.suffix.lower() != ".md":
        return jsonify({"error": "Note introuvable"}), 404
    if p.stat().st_size > MAX_TAILLE:
        return jsonify({"error": "Note trop volumineuse pour l'API (%d octets)" % p.stat().st_size}), 413
    texte = p.read_text(encoding="utf-8", errors="replace")
    return jsonify({"chemin": _relatif(p), "contenu": texte,
                    "provenance": provenance.lire(p)})


def _sans_marqueurs(valeur):
    """Enlève les marqueurs de surlignage `\\x01`/`\\x02` posés pour le navigateur.

    L'interface les remplace par `<mark>`. Un agent, lui, reçoit des caractères de
    contrôle au milieu de son texte : illisibles, et bruyants dans un contexte de
    modèle. Ils sont retirés ici, sur la seule surface qui sert aux agents.
    """
    if isinstance(valeur, str):
        return valeur.replace("\x01", "").replace("\x02", "")
    if isinstance(valeur, list):
        return [_sans_marqueurs(v) for v in valeur]
    if isinstance(valeur, dict):
        return {k: _sans_marqueurs(v) for k, v in valeur.items()}
    return valeur


@bp.route(PREFIX + "/recherche", methods=["GET"])
@exige("lecture")
def recherche():
    texte = (request.args.get("q") or "").strip()
    if len(texte) < 2:
        return jsonify({"error": "Requête trop courte"}), 400
    return jsonify({"resultats": _sans_marqueurs(query.search(fresh_index(), texte))})


@bp.route(PREFIX + "/arbre", methods=["GET"])
@exige("lecture")
def arbre():
    """Recherche en arbre (E13), en lecture seule : la carte des relations et les notes
    retenues, **sans jamais appeler de modèle**.

    Ouvert aux agents parce que c'est précisément là que la mesure d'E13 a montré un
    gain : sur 29 notes retenues, 12 n'étaient remontées par aucun score. Un agent qui
    ne dispose que de la recherche plate paie le même nombre de jetons pour un contexte
    moins bon, et ne voit aucune relation entre les notes.
    """
    from .. import arbre as arbre_mod

    texte = (request.args.get("q") or "").strip()
    depart = (request.args.get("depart") or "").strip()
    if len(texte) < 2 and not depart:
        return jsonify({"error": "Requête trop courte"}), 400
    try:
        depart = str(safe_path(depart)) if depart else None
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403

    racine = vault_root()
    resultat = arbre_mod.construire(fresh_index(racine), texte, depart=depart, racine=racine)
    return jsonify({
        "carte": arbre_mod.carte(resultat["noeuds"]),
        "noeuds": [{"chemin": _relatif(n["chemin"]), "motif": n["motif"],
                    "niveau": n["niveau"], "retenu": n["retenu"]}
                   for n in resultat["noeuds"]],
        "retenus": [_relatif(c) for c in resultat["retenus"]],
        "comptes": resultat["comptes"],
    })


@bp.route(PREFIX + "/objets", methods=["GET"])
@exige("lecture")
def objets():
    return jsonify({"sources": sources.lister(statut=request.args.get("statut") or None)})


# ── Proposition ─────────────────────────────────────────────────────────
@bp.route(PREFIX + "/proposer", methods=["POST"])
@exige("proposition")
def proposer():
    """Dépose une référence dans la file de validation. Rien n'entre dans le vault.

    Même une référence parfaitement vérifiable passe par la file quand elle vient d'un
    agent : la décision 0021 range explicitement les propositions d'agents parmi ce qui
    ne bénéficie jamais de l'entrée directe.
    """
    d = request.get_json(silent=True) or {}
    titre = str(d.get("titre") or "").strip()
    if not titre:
        return jsonify({"error": "Titre requis"}), 400
    brute = str(d.get("reference") or "").strip()
    verifiee = detection.cle_de(brute) if brute else None
    genre = detection.references(brute)[0]["genre"] if verifiee else "texte"
    cle = verifiee or ("texte:" + " ".join(titre.lower().split())[:120])

    note = str(d.get("note") or "").strip()
    if note:
        try:
            p = safe_path(note)
        except PermissionError as e:
            return jsonify({"error": str(e)}), 403
        note = _relatif(p) if p.is_file() else ""

    entree = filedattente.ajouter({
        "cle": cle, "brut": brute or titre, "genre": genre, "titre": titre,
        "origine": trousseau.origine(g.agent["id"], {"nom": g.agent["nom"]}),
        "note": note, "indice": str(d.get("indice") or "").strip(),
        "motif": str(d.get("motif") or "").strip(),
    })
    if entree is None:
        return jsonify({"acceptee": False,
                        "raison": "Déjà en file, déjà rejetée, ou plafond atteint pour cet agent "
                                  "(%d propositions en attente)" % filedattente.PLAFOND_PAR_ORIGINE,
                        "cle": cle}), 409
    return jsonify({"acceptee": True, "entree": entree,
                    "message": "Déposée dans la file. Elle attend la validation de l'auteur."}), 201


@bp.route(PREFIX + "/file", methods=["GET"])
@exige("proposition")
def ma_file():
    """Ce que CET agent a déposé et qui attend encore — pas la file des autres."""
    mienne = trousseau.origine(g.agent["id"], {"nom": g.agent["nom"]})
    entrees = filedattente.lister(origine=mienne)
    return jsonify({"entrees": entrees, "en_attente": len(entrees),
                    "plafond": filedattente.PLAFOND_PAR_ORIGINE})


# ── Écriture directe ────────────────────────────────────────────────────
@bp.route(PREFIX + "/note", methods=["POST"])
@exige("ecriture")
def ecrire_note():
    """Écrit une note. Toujours estampillée au nom de l'agent : une note produite par
    une machine ne doit jamais être indiscernable d'une note écrite à la main."""
    d = request.get_json(silent=True) or {}
    contenu = d.get("contenu")
    if not isinstance(contenu, str) or not contenu.strip():
        return jsonify({"error": "Contenu requis"}), 400
    if len(contenu) > MAX_TAILLE:
        return jsonify({"error": "Contenu trop volumineux"}), 413
    try:
        p = safe_path(d.get("path", ""))
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    if p.suffix.lower() != ".md":
        return jsonify({"error": "Seules les notes .md sont acceptées"}), 400
    if p.is_dir():
        return jsonify({"error": "Un dossier porte déjà ce chemin"}), 400

    estampille = provenance.estampiller(
        contenu, type="note", outil="agent",
        genere_par=g.agent["nom"],
        sources=[str(s) for s in (d.get("sources") or [])],
        extra={"prisme_agent": g.agent["nom"], "prisme_agent_cle": g.agent["id"]})
    existait = p.is_file()
    if existait:
        snapshot(p, force=True)               # ce qu'un agent écrase reste récupérable
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(estampille, encoding="utf-8")
    notify_changed(p)
    return jsonify({"ok": True, "chemin": _relatif(p), "remplacee": existait}), 200 if existait else 201
