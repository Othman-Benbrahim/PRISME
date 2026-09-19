"""Routes de la recherche en arbre : construire, mesurer, répondre."""
from flask import Blueprint, jsonify, request

from .. import arbre as arbre_mod
from ..config import rd_cfg
from ..index import fresh_index
from ..providers import _ai_call, needs_key
from ..vault import racine_de, safe_path, vault_root

bp = Blueprint("arbre", __name__)
PREFIX = "/api/arbre"
MAX_PROFONDEUR = 4
MAX_BUDGET = 200_000


def _corps():
    return request.get_json(silent=True) or {}


def _entier(d, cle, defaut, plafond):
    try:
        return max(1, min(plafond, int(d.get(cle) or defaut)))
    except (TypeError, ValueError):
        return defaut


def _racine_et_index(depart):
    racine = racine_de(depart) if depart else None
    racine = racine or vault_root()
    return racine, fresh_index(racine)


@bp.route(PREFIX + "/construire", methods=["POST"])
def construire():
    """Construit l'arbre et le renvoie SANS appeler le modèle.

    C'est le point de la décision 0029 : on voit l'arbre, on élague, et seulement
    ensuite on demande une réponse.
    """
    d = _corps()
    question = str(d.get("question") or "").strip()
    depart = str(d.get("depart") or "").strip()
    if not question and not depart:
        return jsonify({"error": "Donnez une question, une note de départ, ou les deux"}), 400
    try:
        if depart:
            depart = str(safe_path(depart))
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403

    racine, index = _racine_et_index(depart)
    resultat = arbre_mod.construire(
        index, question, depart=depart or None,
        profondeur=_entier(d, "profondeur", arbre_mod.PROFONDEUR, MAX_PROFONDEUR),
        budget=_entier(d, "budget", arbre_mod.BUDGET, MAX_BUDGET),
        racine=racine)
    resultat["racine"] = str(racine)
    if question and d.get("comparer"):
        resultat["comparaison"] = arbre_mod.comparer(index, question, resultat, racine=racine)
    return jsonify(resultat)


@bp.route(PREFIX + "/repondre", methods=["POST"])
def repondre():
    """Répond à partir des nœuds retenus. L'arbre a déjà été vu et élagué."""
    d = _corps()
    question = str(d.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Question vide"}), 400
    arbre = d.get("arbre") or {}
    if not arbre.get("noeuds"):
        return jsonify({"error": "Arbre absent : construisez-le d'abord"}), 400
    retenus = d.get("retenus")
    if retenus is not None:
        # L'arbre revient du navigateur : on ne lit que des chemins qui y figurent.
        # Sans ce filtre, une requête forgée ferait lire n'importe quel fichier via la
        # liste « retenus ». safe_path protégerait encore, mais en silence : mieux vaut
        # refuser ici, où l'on sait que c'est une tentative et pas une note effacée.
        connus = {n.get("chemin") for n in arbre["noeuds"]}
        retenus = [c for c in retenus if c in connus]
        if not retenus:
            return jsonify({"error": "Aucune note retenue — cochez-en au moins une"}), 400

    cfg = rd_cfg()
    if needs_key(cfg):
        return jsonify({"error": "Clé API manquante — configurez-la dans Paramètres."}), 400
    try:
        contexte, detail = arbre_mod.assembler(arbre, retenus)
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403

    reponse, erreur = _ai_call(
        cfg,
        [{"role": "system", "content": arbre_mod.contexte.CONSIGNE},
         {"role": "user", "content": "%s\n\n---\n\n%s" % (contexte, question)}],
        max_tokens=2000, temp=0.3, timeout=120)
    if erreur:
        return jsonify({"error": erreur}), 502
    return jsonify({"reponse": reponse, "notes": detail,
                    "caracteres_envoyes": len(contexte)})
