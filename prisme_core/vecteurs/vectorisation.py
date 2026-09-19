"""Construction et mise à jour des vecteurs à partir de l'index (docs/decisions/0019).

Seuls les segments dont l'empreinte est inconnue du magasin sont envoyés au
fournisseur : réindexer un vault ne revectorise que ce qui a bougé. C'est ce qui rend
l'opération supportable quand elle est payante ou lente.
"""
import threading
import time

from ..config import rd_cfg
from .contrat import VecteurIndisponible, construire
from .magasin import magasin_pour

ETAT = {"en_cours": False, "faits": 0, "total": 0, "message": "", "erreur": "",
        "commence_le": 0.0, "duree": 0.0}
_VERROU = threading.Lock()


def fournisseur_configure(cfg=None):
    """Le fournisseur choisi, ou None si la vectorisation est désactivée.

    Désactivée est l'état par défaut : vectoriser un vault, c'est parfois en envoyer le
    contenu à un tiers (docs/decisions/0019).
    """
    cfg = cfg or rd_cfg()
    if not cfg.get("emb_actif"):
        return None
    return construire(cfg.get("emb_fournisseur") or "api", cfg)


def etat(cfg=None):
    """De quoi afficher en permanence ce qui est actif, comme l'exige 0019."""
    cfg = cfg or rd_cfg()
    magasin = magasin_pour()
    base = {"actif": bool(cfg.get("emb_actif")), "fournisseur": cfg.get("emb_fournisseur") or "api",
            "modele": cfg.get("emb_modele") or "", **magasin.etat(),
            "progression": dict(ETAT)}
    if not base["actif"]:
        base.update({"disponible": False, "distant": None,
                     "raison": "Recherche sémantique désactivée — recherche lexicale seule"})
        return base
    try:
        f = fournisseur_configure(cfg)
        ok, raison = f.disponible()
        base.update({"disponible": ok, "raison": raison, "distant": bool(f.distant),
                     "signature_attendue": f.signature() if ok else ""})
    except VecteurIndisponible as e:
        base.update({"disponible": False, "raison": str(e), "distant": None})
    return base


def _segments_a_faire(index, magasin):
    """(à vectoriser, toutes les empreintes vivantes)."""
    with index.read() as conn:
        lignes = conn.execute(
            "SELECT DISTINCT sha256, text FROM segments WHERE length(trim(text)) > 0").fetchall()
    connus = magasin.connus()
    vivants = {r["sha256"] for r in lignes}
    return [(r["sha256"], r["text"]) for r in lignes if r["sha256"] not in connus], vivants


def vectoriser(index=None, cfg=None, par_lot=64):
    """Met le magasin à jour. Renvoie un compte rendu ; ne lève pas."""
    from ..index import fresh_index

    cfg = cfg or rd_cfg()
    with _VERROU:
        if ETAT["en_cours"]:
            return {"error": "Une vectorisation est déjà en cours", **dict(ETAT)}
        ETAT.update({"en_cours": True, "faits": 0, "total": 0, "message": "Préparation…",
                     "erreur": "", "commence_le": time.time(), "duree": 0.0})
    try:
        fournisseur = fournisseur_configure(cfg)
        if fournisseur is None:
            raise VecteurIndisponible("Recherche sémantique désactivée dans les Paramètres")
        ok, raison = fournisseur.disponible()
        if not ok:
            raise VecteurIndisponible(raison)

        index = index or fresh_index()
        magasin = magasin_pour()
        # Changer de modèle vide le magasin : un index ne mélange jamais deux modèles.
        revectorise = magasin.fixer_signature(fournisseur.signature())

        a_faire, vivants = _segments_a_faire(index, magasin)
        oublies = magasin.oublier_absents(vivants)
        ETAT.update({"total": len(a_faire), "message": "Vectorisation…"})

        for debut in range(0, len(a_faire), par_lot):
            lot = a_faire[debut:debut + par_lot]
            vecteurs = fournisseur.vectoriser_role([t for _s, t in lot], role="passage")
            magasin.enregistrer(list(zip([s for s, _t in lot], vecteurs)))
            ETAT["faits"] = min(debut + par_lot, len(a_faire))
        return {"ok": True, "vectorises": len(a_faire), "oublies": oublies,
                "revectorisation": revectorise, "total_magasin": magasin.compte(),
                "signature": fournisseur.signature(),
                "duree": round(time.time() - ETAT["commence_le"], 1)}
    except VecteurIndisponible as e:
        ETAT["erreur"] = str(e)
        return {"error": str(e)}
    except Exception as e:                                            # noqa: BLE001
        ETAT["erreur"] = "%s: %s" % (type(e).__name__, str(e)[:200])
        return {"error": ETAT["erreur"]}
    finally:
        ETAT["duree"] = round(time.time() - ETAT["commence_le"], 1)
        ETAT["en_cours"] = False
        ETAT["message"] = ""


def lancer_en_fond(index=None):
    """Vectorisation en tâche de fond : l'interface reste utilisable pendant ce temps."""
    if ETAT["en_cours"]:
        return False
    threading.Thread(target=lambda: vectoriser(index), name="prisme-vecteurs", daemon=True).start()
    return True
