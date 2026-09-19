"""Contrat des fournisseurs d'embeddings (docs/decisions/0019).

Un fournisseur transforme des textes en vecteurs. Le cœur en connaît deux — une API
compatible OpenAI et Ollama — et un plugin peut en enregistrer d'autres, dont le
fournisseur local ONNX, qui ne peut pas vivre dans le cœur : il embarque une
bibliothèque compilée et un modèle de plusieurs dizaines de mégaoctets.

Deux règles structurent tout le reste :

- **Un index ne mélange jamais deux modèles.** La signature d'un fournisseur
  (`fournisseur:modèle:dimension`) est enregistrée avec les vecteurs ; en changer
  invalide le magasin et déclenche une revectorisation annoncée.
- **Un fournisseur distant est désactivé par défaut.** Vectoriser, c'est envoyer le
  texte de ses notes à un tiers : ça ne s'active jamais sans un geste explicite.
"""

MAX_LOT = 64                # textes par appel ; au-delà, les API refusent ou ralentissent
MAX_CAR = 8000              # un segment plus long est tronqué avant l'envoi


class VecteurIndisponible(RuntimeError):
    """Le fournisseur ne peut pas répondre. La recherche retombe sur FTS5 seul."""


class Fournisseur:
    """À implémenter pour ajouter une source de vecteurs."""

    nom = ""
    distant = True          # True = les textes sortent de la machine

    def modele(self):
        raise NotImplementedError

    def dimension(self):
        """Taille des vecteurs produits. Peut nécessiter un appel de sonde."""
        raise NotImplementedError

    def disponible(self):
        """(True, '') si utilisable, (False, raison) sinon. Ne lève jamais."""
        raise NotImplementedError

    def vectoriser(self, textes):
        """[[float]] dans l'ordre des textes. Lève VecteurIndisponible en cas d'échec."""
        raise NotImplementedError

    # ── Commun ───────────────────────────────────────────────────────────
    def signature(self):
        """Ce qui doit rester identique d'un bout à l'autre d'un magasin de vecteurs."""
        return "%s:%s:%d" % (self.nom, self.modele(), self.dimension())

    def decrire(self):
        ok, raison = self.disponible()
        return {"nom": self.nom, "modele": self.modele(), "distant": self.distant,
                "disponible": ok, "raison": raison}


_REGISTRE = {}


def enregistrer(fabrique, nom=None):
    """Ajoute un fournisseur. `fabrique(cfg)` renvoie une instance de Fournisseur.

    Décorateur utilisable depuis un plugin :

        @enregistrer
        class FournisseurOnnx(Fournisseur):
            nom = "onnx"
    """
    if isinstance(fabrique, type) and issubclass(fabrique, Fournisseur):
        _REGISTRE[nom or fabrique.nom] = fabrique
        return fabrique
    _REGISTRE[nom] = fabrique
    return fabrique


def noms():
    return sorted(_REGISTRE)


def construire(nom, cfg):
    """Instancie un fournisseur enregistré. Lève VecteurIndisponible s'il est inconnu."""
    fabrique = _REGISTRE.get(nom)
    if fabrique is None:
        raise VecteurIndisponible(
            "Fournisseur d'embeddings inconnu : %s (connus : %s)" % (nom, ", ".join(noms()) or "aucun"))
    return fabrique(cfg)


def par_lots(textes, taille=MAX_LOT):
    lot = []
    for t in textes:
        lot.append((t or "")[:MAX_CAR])
        if len(lot) >= taille:
            yield lot
            lot = []
    if lot:
        yield lot
