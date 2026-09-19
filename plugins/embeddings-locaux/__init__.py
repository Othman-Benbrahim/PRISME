"""Embeddings locaux par ONNX Runtime (docs/decisions/0019).

Ce plugin est l'exception assumée à la règle « bibliothèque standard seulement » : il
embarque deux dépendances compilées — `onnxruntime` et `tokenizers` — et fait tourner un
modèle e5 quantifié sur le processeur. En échange, **rien ne sort de la machine** : ni
les notes qu'on vectorise, ni les recherches qu'on tape.

Le cœur ne peut pas porter ça : une bibliothèque compilée et un modèle de cent
mégaoctets n'ont rien à faire dans un exécutable qui doit rester portable. Un plugin,
lui, s'installe et se désinstalle.

Si les bibliothèques manquent, le plugin se charge quand même : seul le fournisseur se
déclare indisponible, en disant quoi installer. PRISME retombe alors sur la recherche
par mots, comme il le fait pour n'importe quel fournisseur absent.
"""
import json
import threading
import time
from pathlib import Path

from . import modele, moteur

# Modeles connus, a titre de commodite. Les URL ne sont PAS verifiees par PRISME :
# telecharger vous-meme et indiquer un dossier reste la voie la plus sure.
CATALOGUE = {
    "multilingual-e5-small": {
        "libelle": "multilingual-e5-small (quantifié) — 100 langues, ~120 Mo",
        "dimension": 384,
        "prefixes": True,
        "fichiers": {
            "model.onnx": "https://huggingface.co/Xenova/multilingual-e5-small/resolve/main/onnx/model_quantized.onnx",
            "tokenizer.json": "https://huggingface.co/Xenova/multilingual-e5-small/resolve/main/tokenizer.json",
        },
    },
    "multilingual-e5-base": {
        "libelle": "multilingual-e5-base (quantifié) — meilleur, ~280 Mo",
        "dimension": 768,
        "prefixes": True,
        "fichiers": {
            "model.onnx": "https://huggingface.co/Xenova/multilingual-e5-base/resolve/main/onnx/model_quantized.onnx",
            "tokenizer.json": "https://huggingface.co/Xenova/multilingual-e5-base/resolve/main/tokenizer.json",
        },
    },
}

REGLAGES = "reglages.json"
TELECHARGEMENT = {"en_cours": False, "fichier": "", "faits": 0, "total": 0, "erreur": "", "fini": ""}
_MOTEURS = {}
_VERROU = threading.Lock()


def register(ctx):
    """Point d'entrée du plugin."""

    def dossier_modeles():
        d = ctx.data_dir() / "modeles"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def fichier_reglages():
        return ctx.data_dir() / REGLAGES

    def lire_reglages():
        try:
            r = json.loads(fichier_reglages().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            r = {}
        r.setdefault("dossier", str(dossier_modeles() / "multilingual-e5-small"))
        r.setdefault("nom", "multilingual-e5-small")
        r.setdefault("prefixes", True)
        r.setdefault("fils", 0)
        r.setdefault("empreintes", {})
        return r

    def ecrire_reglages(r):
        fichier_reglages().write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")

    def moteur_courant():
        """Un moteur par dossier : charger un modele coute cher, on ne le refait pas."""
        r = lire_reglages()
        cle = (r["dossier"], bool(r["prefixes"]), int(r.get("fils") or 0))
        with _VERROU:
            m = _MOTEURS.get(cle)
            if m is None:
                m = _MOTEURS[cle] = moteur.Moteur(r["dossier"], prefixes=r["prefixes"],
                                                  fils=r.get("fils") or None)
            return m, r

    # ── Le fournisseur d'embeddings ──────────────────────────────────────
    class EmbeddingsLocaux(ctx.EmbeddingProvider):
        nom = "onnx"
        distant = False          # la raison d'etre de ce plugin

        def __init__(self, cfg):
            self.cfg = cfg or {}

        def modele(self):
            return lire_reglages()["nom"]

        def dimension(self):
            m, _r = moteur_courant()
            try:
                return m.dimension()
            except moteur.MoteurIndisponible as e:
                raise ctx.EmbeddingUnavailable(str(e))

        def disponible(self):
            ok, message = moteur.dependances()
            if not ok:
                return False, message
            r = lire_reglages()
            _d, manquants = modele.valider_dossier(r["dossier"])
            if manquants:
                return False, ("Modèle absent de %s : %s manquant(s). Ouvrez Paramètres → "
                               "Embeddings locaux pour l'installer." % (r["dossier"], ", ".join(manquants)))
            try:
                self.dimension()
            except ctx.EmbeddingUnavailable as e:
                return False, str(e)
            return True, ""

        def prefixe(self, role):
            # Le moteur pose deja le prefixe : le coeur ne doit pas le doubler.
            return ""

        def vectoriser(self, textes):
            return self.vectoriser_role(textes, role="passage")

        def vectoriser_role(self, textes, role="passage"):
            m, _r = moteur_courant()
            try:
                return m.encoder(textes, role=role)
            except moteur.MoteurIndisponible as e:
                raise ctx.EmbeddingUnavailable(str(e))

    ctx.register_embeddings(EmbeddingsLocaux)

    # ── Routes ───────────────────────────────────────────────────────────
    @ctx.route("/etat")
    def etat():
        r = lire_reglages()
        ok, message = moteur.dependances()
        return {
            "dependances_ok": ok, "dependances": message,
            "reglages": {k: v for k, v in r.items() if k != "empreintes"},
            "modele": modele.decrire(r["dossier"]),
            "catalogue": {k: {"libelle": v["libelle"], "dimension": v["dimension"]}
                          for k, v in CATALOGUE.items()},
            "dossier_par_defaut": str(dossier_modeles()),
            "telechargement": dict(TELECHARGEMENT),
        }

    @ctx.route("/reglages", methods=["POST"])
    def reglages():
        from flask import request
        d = request.get_json(silent=True) or {}
        r = lire_reglages()
        if "dossier" in d:
            r["dossier"] = str(d["dossier"] or "").strip() or r["dossier"]
        if "nom" in d:
            r["nom"] = str(d["nom"] or "").strip()[:60] or r["nom"]
        if "prefixes" in d:
            r["prefixes"] = bool(d["prefixes"])
        if "fils" in d:
            try:
                r["fils"] = max(0, min(32, int(d["fils"] or 0)))
            except (TypeError, ValueError):
                return {"error": "Nombre de fils invalide"}, 400
        ecrire_reglages(r)
        with _VERROU:
            _MOTEURS.clear()                 # les reglages changent : on recharge
        return etat()

    @ctx.route("/epingler", methods=["POST"])
    def epingler():
        """Fige l'empreinte du modèle actuellement installé : tout écart sera refusé."""
        r = lire_reglages()
        info = modele.decrire(r["dossier"])
        if not info.get("present"):
            return {"error": "Aucun modèle complet à épingler"}, 400
        r.setdefault("empreintes", {})[r["nom"]] = {"model.onnx": info["sha256"]}
        ecrire_reglages(r)
        return {"ok": True, "sha256": info["sha256"]}

    @ctx.route("/installer", methods=["POST"])
    def installer():
        """Télécharge un modèle du catalogue, ou depuis des URL fournies."""
        from flask import request
        d = request.get_json(silent=True) or {}
        nom = str(d.get("nom") or "").strip()
        fichiers = d.get("fichiers") or {}
        dimension_attendue = None
        prefixes = True
        if nom in CATALOGUE:
            entree = CATALOGUE[nom]
            fichiers = fichiers or entree["fichiers"]
            dimension_attendue = entree["dimension"]
            prefixes = entree["prefixes"]
        elif not fichiers:
            return {"error": "Modèle inconnu et aucune URL fournie"}, 400

        if TELECHARGEMENT["en_cours"]:
            return {"error": "Un téléchargement est déjà en cours"}, 409
        cible = Path(d.get("dossier") or (dossier_modeles() / (nom or "modele")))

        def progression(fichier, faits, total):
            TELECHARGEMENT.update({"fichier": fichier, "faits": faits, "total": total})

        def travail():
            TELECHARGEMENT.update({"en_cours": True, "erreur": "", "fini": "",
                                   "faits": 0, "total": 0, "fichier": ""})
            try:
                r = lire_reglages()
                empreintes = (r.get("empreintes") or {}).get(nom or "", {})
                modele.installer(fichiers, cible, progression=progression, empreintes=empreintes)
                r["dossier"] = str(cible)
                if nom:
                    r["nom"] = nom
                r["prefixes"] = prefixes
                ecrire_reglages(r)
                with _VERROU:
                    _MOTEURS.clear()
                TELECHARGEMENT["fini"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                ctx.log("modèle installé dans %s" % cible)
            except modele.ModeleInvalide as e:
                TELECHARGEMENT["erreur"] = str(e)
                ctx.log("échec : %s" % e)
            except Exception as e:                                    # noqa: BLE001
                TELECHARGEMENT["erreur"] = "%s: %s" % (type(e).__name__, str(e)[:160])
            finally:
                TELECHARGEMENT["en_cours"] = False

        threading.Thread(target=travail, name="prisme-modele", daemon=True).start()
        return {"lance": True, "dossier": str(cible), "dimension_attendue": dimension_attendue}

    @ctx.route("/essai", methods=["POST"])
    def essai():
        """Vectorise deux phrases et renvoie leur proximité : le test qui dit tout."""
        from flask import request
        d = request.get_json(silent=True) or {}
        a = str(d.get("a") or "La prédiction calibrée demande un horizon.")
        b = str(d.get("b") or "Anticiper demande de se donner une échéance.")
        c = str(d.get("c") or "Faire revenir les oignons dans l'huile.")
        m, _r = moteur_courant()
        try:
            debut = time.time()
            va, vb, vc = m.encoder([a, b, c], role="passage")
            duree = time.time() - debut
        except moteur.MoteurIndisponible as e:
            return {"error": str(e)}, 400
        cos = lambda x, y: sum(p * q for p, q in zip(x, y))            # noqa: E731
        return {"ok": True, "dimension": len(va), "duree_s": round(duree, 2),
                "proche": round(cos(va, vb), 3), "lointain": round(cos(va, vc), 3),
                "verdict": ("Le modèle distingue bien les deux" if cos(va, vb) > cos(va, vc) + 0.05
                            else "Le modèle ne distingue pas ces phrases — vérifiez le modèle "
                                 "et les préfixes")}
