"""Les deux fournisseurs d'embeddings du cœur (docs/decisions/0019).

- `api` : tout service exposant `/embeddings` à la manière d'OpenAI ;
- `ollama` : une instance locale d'Ollama.

Paramétrage **séparé de celui du chat** : on peut vouloir un modèle local pour écrire
et une API pour vectoriser, ou l'inverse. Les clés vivent dans `config.json`, chiffrées
comme celle du chat.
"""
import json

import requests as http

from .contrat import Fournisseur, VecteurIndisponible, enregistrer, par_lots

DELAI = 120


def _local(url):
    return any(h in (url or "") for h in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]"))


def _extraire(charge):
    """Sort les vecteurs d'une réponse, quelle que soit la forme du service."""
    if isinstance(charge, dict):
        if isinstance(charge.get("data"), list):                     # OpenAI
            return [d.get("embedding") for d in charge["data"]]
        if isinstance(charge.get("embeddings"), list):               # Ollama (lot)
            return charge["embeddings"]
        if isinstance(charge.get("embedding"), list):                # Ollama (unitaire)
            return [charge["embedding"]]
    raise VecteurIndisponible("Réponse illisible : %s" % json.dumps(charge)[:200])


def _verifier(vecteurs, attendus):
    if len(vecteurs) != attendus or any(not v for v in vecteurs):
        raise VecteurIndisponible(
            "Le service a renvoyé %d vecteur(s) pour %d texte(s)" % (len(vecteurs), attendus))
    return [[float(x) for x in v] for v in vecteurs]


class _Http(Fournisseur):
    """Base commune : un appel HTTP, une dimension sondée une fois et retenue."""

    def __init__(self, cfg):
        self.cfg = cfg or {}
        self._dim = None

    def modele(self):
        return (self.cfg.get("emb_modele") or "").strip()

    def base(self):
        return (self.cfg.get("emb_base_url") or "").rstrip("/")

    def dimension(self):
        if self._dim is None:
            sonde = self.vectoriser(["sonde"])
            self._dim = len(sonde[0])
        return self._dim

    def disponible(self):
        if not self.base():
            return False, "Adresse du service non renseignée"
        if not self.modele():
            return False, "Modèle d'embeddings non renseigné"
        try:
            self.vectoriser(["sonde"])
        except VecteurIndisponible as e:
            return False, str(e)
        return True, ""

    def _poster(self, url, entetes, corps):
        try:
            r = http.post(url, headers=entetes, json=corps, timeout=DELAI)
        except http.exceptions.Timeout:
            raise VecteurIndisponible("Délai dépassé (%d s) — modèle trop lent ou service figé" % DELAI)
        except Exception as e:                                        # noqa: BLE001
            raise VecteurIndisponible("Réseau : %s: %s" % (type(e).__name__, str(e)[:160]))
        if r.status_code != 200:
            raise VecteurIndisponible("HTTP %d : %s" % (r.status_code, (r.text or "")[:200]))
        r.encoding = "utf-8"
        try:
            return r.json()
        except ValueError:
            raise VecteurIndisponible("Réponse non JSON : %s" % (r.text or "")[:200])


@enregistrer
class FournisseurApi(_Http):
    """Service compatible OpenAI : POST <base>/embeddings."""

    nom = "api"

    @property
    def distant(self):
        return not _local(self.base())

    def vectoriser(self, textes):
        textes = list(textes)
        if not textes:
            return []
        entetes = {"Content-Type": "application/json"}
        cle = (self.cfg.get("emb_api_key") or "").strip()
        if cle:
            entetes["Authorization"] = "Bearer " + cle
        out = []
        for lot in par_lots(textes):
            charge = self._poster(self.base() + "/embeddings", entetes,
                                  {"model": self.modele(), "input": lot})
            out.extend(_extraire(charge))
        return _verifier(out, len(textes))


@enregistrer
class FournisseurOllama(_Http):
    """Ollama local : POST <base>/api/embed. Rien ne sort de la machine."""

    nom = "ollama"
    distant = False

    def base(self):
        return (self.cfg.get("emb_base_url") or "http://127.0.0.1:11434").rstrip("/")

    def vectoriser(self, textes):
        textes = list(textes)
        if not textes:
            return []
        out = []
        for lot in par_lots(textes):
            charge = self._poster(self.base() + "/api/embed",
                                  {"Content-Type": "application/json"},
                                  {"model": self.modele(), "input": lot})
            out.extend(_extraire(charge))
        return _verifier(out, len(textes))
