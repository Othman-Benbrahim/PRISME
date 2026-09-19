"""Gestion des racines de vault (docs/decisions/0028).

La racine principale reste `workspace` : c'est elle qu'un chemin relatif désigne, celle
où une note nouvelle atterrit, et la seule qu'une clé d'agent voit par défaut. Les autres
s'ajoutent et se retirent ici.
"""
from pathlib import Path

from flask import Blueprint, jsonify, request

from ..config import rd_cfg, wr_cfg
from ..vault import ensure_vault, vault_roots

bp = Blueprint("racines", __name__)
PREFIX = "/api/racines"
MAX_RACINES = 8          # au-dela, chercher partout devient lent et le reglage illisible


def _etat():
    racines = vault_roots()
    out = []
    for i, r in enumerate(racines):
        existe = r.is_dir()
        out.append({"chemin": str(r), "nom": r.name, "principale": i == 0,
                    "existe": existe,
                    "notes": sum(1 for _ in r.glob("*.md")) if existe else 0})
    return {"racines": out, "plafond": MAX_RACINES}


@bp.route(PREFIX, methods=["GET"])
def lister():
    return jsonify(_etat())


@bp.route(PREFIX, methods=["POST"])
def ajouter():
    """Déclare une racine supplémentaire. Le dossier doit exister : on ne crée pas
    silencieusement un vault à partir d'une faute de frappe."""
    d = request.get_json(silent=True) or {}
    brut = str(d.get("chemin") or "").strip()
    if not brut:
        return jsonify({"error": "Chemin vide"}), 400
    try:
        p = Path(brut).expanduser().resolve()
    except OSError:
        return jsonify({"error": "Chemin invalide"}), 400
    if not p.is_dir():
        return jsonify({"error": "Dossier introuvable : %s" % p}), 404

    racines = vault_roots()
    if any(p == r for r in racines):
        return jsonify({"error": "Racine déjà déclarée"}), 409
    # Une racine imbriquee dans une autre ferait appartenir un meme fichier a deux index.
    for r in racines:
        if r in p.parents:
            return jsonify({"error": "Ce dossier est déjà couvert par la racine %s" % r}), 409
        if p in r.parents:
            return jsonify({"error": "Ce dossier contient la racine %s — déclarez-le "
                                     "à la place de celle-ci, ou choisissez plus bas" % r}), 409
    if len(racines) >= MAX_RACINES:
        return jsonify({"error": "Plafond atteint (%d racines)" % MAX_RACINES}), 409

    cfg = rd_cfg()
    wr_cfg({"workspaces": list(cfg.get("workspaces") or []) + [str(p)]})
    return jsonify(_etat()), 201


@bp.route(PREFIX + "/retirer", methods=["POST"])
def retirer():
    """Retire une racine de la liste. **Aucun fichier n'est touché** : on cesse
    seulement de la regarder."""
    d = request.get_json(silent=True) or {}
    try:
        p = Path(str(d.get("chemin") or "")).expanduser().resolve()
    except OSError:
        return jsonify({"error": "Chemin invalide"}), 400
    cfg = rd_cfg()
    if str(p) == str(Path(cfg.get("workspace") or "").expanduser().resolve()):
        return jsonify({"error": "La racine principale ne se retire pas : "
                                 "changez-la dans Paramètres"}), 400
    restantes = [x for x in (cfg.get("workspaces") or [])
                 if str(Path(x).expanduser().resolve()) != str(p)]
    if len(restantes) == len(cfg.get("workspaces") or []):
        return jsonify({"error": "Racine inconnue"}), 404
    wr_cfg({"workspaces": restantes})
    return jsonify(_etat())


@bp.route(PREFIX + "/principale", methods=["POST"])
def principale():
    """Promeut une racine déclarée au rang de principale. L'ancienne reste déclarée."""
    d = request.get_json(silent=True) or {}
    try:
        p = Path(str(d.get("chemin") or "")).expanduser().resolve()
    except OSError:
        return jsonify({"error": "Chemin invalide"}), 400
    if not p.is_dir():
        return jsonify({"error": "Dossier introuvable"}), 404
    cfg = rd_cfg()
    ancienne = str(Path(cfg.get("workspace") or "").expanduser().resolve())
    autres = [x for x in (cfg.get("workspaces") or [])
              if str(Path(x).expanduser().resolve()) not in (str(p), ancienne)]
    if ancienne and ancienne != str(p):
        autres.insert(0, ancienne)
    ensure_vault(p)
    wr_cfg({"workspace": str(p), "workspaces": autres})
    return jsonify(_etat())
