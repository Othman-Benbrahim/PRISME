"""Routes de la recherche sémantique : état, vectorisation, diagnostic."""
from flask import Blueprint, jsonify, request

from ..config import rd_cfg, wr_cfg
from ..vecteurs import contrat, magasin, vectorisation

bp = Blueprint("vecteurs", __name__)
PREFIX = "/api/vecteurs"


@bp.route(PREFIX + "/etat", methods=["GET"])
def etat():
    """Ce qui est actif, où, et avec quoi. Consulté en permanence par l'interface."""
    return jsonify({**vectorisation.etat(), "fournisseurs": contrat.noms()})


@bp.route(PREFIX + "/tester", methods=["POST"])
def tester():
    """Sonde le fournisseur sans rien écrire : dit s'il répond et en quelle dimension."""
    d = request.get_json(silent=True) or {}
    cfg = {**rd_cfg(), **{k: v for k, v in d.items() if k.startswith("emb_")}, "emb_actif": True}
    try:
        f = contrat.construire(cfg.get("emb_fournisseur") or "api", cfg)
        ok, raison = f.disponible()
        if not ok:
            return jsonify({"ok": False, "raison": raison}), 200
        return jsonify({"ok": True, "modele": f.modele(), "dimension": f.dimension(),
                        "distant": bool(f.distant), "signature": f.signature()})
    except contrat.VecteurIndisponible as e:
        return jsonify({"ok": False, "raison": str(e)}), 200


@bp.route(PREFIX + "/vectoriser", methods=["POST"])
def vectoriser():
    d = request.get_json(silent=True) or {}
    if d.get("fond"):
        return jsonify({"lance": vectorisation.lancer_en_fond(), **vectorisation.ETAT})
    resultat = vectorisation.vectoriser()
    return (jsonify(resultat), 400) if resultat.get("error") else jsonify(resultat)


@bp.route(PREFIX + "/progression", methods=["GET"])
def progression():
    return jsonify(dict(vectorisation.ETAT))


@bp.route(PREFIX + "/vider", methods=["POST"])
def vider():
    """Efface les vecteurs. L'index et les notes ne sont pas touchés."""
    m = magasin.magasin_pour()
    avant = m.compte()
    m.vider()
    return jsonify({"ok": True, "supprimes": avant})


@bp.route(PREFIX + "/config", methods=["POST"])
def config():
    """Enregistre le paramétrage des embeddings, sans toucher à celui du chat."""
    d = request.get_json(silent=True) or {}
    champs = {k: d[k] for k in ("emb_actif", "emb_fournisseur", "emb_base_url",
                                "emb_modele", "emb_api_key", "emb_seuil") if k in d}
    if "emb_seuil" in champs:
        try:
            champs["emb_seuil"] = min(0.95, max(0.0, float(champs["emb_seuil"])))
        except (TypeError, ValueError):
            return jsonify({"error": "Seuil invalide : un nombre entre 0 et 0,95"}), 400
    if "emb_fournisseur" in champs and champs["emb_fournisseur"] not in contrat.noms():
        return jsonify({"error": "Fournisseur inconnu : %s" % champs["emb_fournisseur"]}), 400
    if "emb_actif" in champs:
        champs["emb_actif"] = bool(champs["emb_actif"])
    wr_cfg(champs)
    return jsonify(vectorisation.etat())
