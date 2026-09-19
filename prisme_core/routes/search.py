"""Recherche plein texte, sémantique et multi-racines ; tags et état de l'index."""
from flask import Blueprint, jsonify, request

from ..index import fresh_index, get_index
from ..index import search as query
from ..vault import racine_de, scoped_dir, vault_root, vault_roots
from ..vecteurs.quantification import fusionner

bp = Blueprint("search", __name__)


def _scope():
    scoped = scoped_dir(request.args.get("dir"))
    return None if scoped in {str(r) for r in vault_roots()} else scoped


def _racines_a_chercher(scope):
    """Les racines concernées : toutes, ou la seule qui contient le dossier demandé."""
    if not scope:
        return vault_roots()
    r = racine_de(scope)
    return [r] if r else [vault_root()]


def _chercher_partout(texte, scope, mode):
    """Cherche dans chaque racine et fusionne par RRF (docs/decisions/0028).

    Un index par racine, donc des scores BM25 qui ne sont **pas comparables** d'une
    racine à l'autre — une note d'un petit vault obtiendrait mécaniquement un meilleur
    score qu'une note équivalente d'un gros. RRF ne compare que des rangs, ce qui rend
    la fusion honnête ; c'est déjà ce qui sert à marier lexical et sémantique en E7.
    """
    from ..vecteurs.recherche import hybride

    racines = _racines_a_chercher(scope)
    par_racine, etats, infos = [], [], {"mode": "lexical", "semantique": False, "repli": ""}
    for r in racines:
        idx = fresh_index(r)
        etats.append({"racine": str(r), "state": idx.state, "progress": idx.progress})
        if mode == "lexical":
            resultats = query.search(idx, texte, root_filter=scope)
            info = {"mode": "lexical", "semantique": False, "repli": ""}
        else:
            resultats, info = hybride(idx, texte, root_filter=scope, racine=r)
        for x in resultats:
            x["racine"] = str(r)
        par_racine.append(resultats)
        # Le mode affiché est le meilleur obtenu : si une seule racine a des vecteurs,
        # la recherche est bien hybride quelque part, et le repli de l'autre le dit.
        if info.get("semantique"):
            infos["semantique"] = True
            infos["mode"] = "hybride"
        elif info.get("repli") and not infos["repli"]:
            infos["repli"] = info["repli"]

    if len(par_racine) == 1:
        return par_racine[0], infos, etats

    par_chemin = {x["path"]: x for liste in par_racine for x in liste}
    classements = [[x["path"] for x in liste] for liste in par_racine]
    fusion = fusionner(*classements)
    return [par_chemin[chemin] for chemin, _score in fusion if chemin in par_chemin], infos, etats


@bp.route("/api/search", methods=["GET"])
def search_files():
    text = request.args.get("q", "").strip()
    # Le perimetre est verifie AVANT la longueur : une requete trop courte ne doit pas
    # faire passer un dossier interdit pour acceptable.
    try:
        scope = _scope()
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    if len(text) < 2:
        return jsonify({"results": []})
    mode = "lexical" if request.args.get("mode") == "lexical" else "hybride"
    resultats, info, etats = _chercher_partout(text, scope, mode)
    principal = etats[0] if etats else {"state": "vide", "progress": {}}
    return jsonify({"results": resultats, "recherche": info,
                    "index": {"state": principal["state"], "progress": principal["progress"]},
                    "index_par_racine": etats})


@bp.route("/api/tags", methods=["GET"])
def get_tags():
    """Tags d'une racine. Les tags ne traversent pas les racines : deux vaults sont
    deux ensembles de notes, pas un seul éclaté (docs/decisions/0028)."""
    try:
        scope = _scope()
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    racine = _racines_a_chercher(scope)[0]
    return jsonify({"tags": query.tags(fresh_index(racine), scope), "racine": str(racine)})


@bp.route("/api/index/status", methods=["GET"])
def index_status():
    racines = vault_roots()
    etats = []
    for i, r in enumerate(racines):
        etat = get_index(r).status()
        etats.append({**etat, "racine": str(r), "nom": r.name, "principale": i == 0})
    return jsonify({**etats[0], "racines": etats})


@bp.route("/api/index/rebuild", methods=["POST"])
def index_rebuild():
    """Reconstruit l'index d'une racine, ou de toutes si aucune n'est précisée."""
    d = request.get_json(silent=True) or {}
    cible = (d.get("racine") or "").strip()
    racines = vault_roots()
    if cible:
        choisie = racine_de(cible)
        if choisie is None:
            return jsonify({"error": "Racine inconnue : %s" % cible}), 404
        racines = [choisie]
    lances = []
    for r in racines:
        idx = get_index(r)
        lances.append({"racine": str(r), "started": idx.start_background(rebuild=True), **idx.status()})
    return jsonify({"started": any(x["started"] for x in lances), "racines": lances})
