"""Exécution du modèle : tokenisation, inférence ONNX, agrégation.

Trois détails décident de la qualité, et se trompent en silence si on les néglige :

- **Le préfixe de rôle.** La famille e5 attend « query: » devant une requête et
  « passage: » devant un document. Sans eux, tout fonctionne et les résultats sont
  médiocres, sans que rien ne le signale.
- **L'agrégation.** e5 veut une moyenne sur les jetons **pondérée par le masque
  d'attention** : compter le remplissage fausse la moyenne des textes courts.
- **La normalisation.** Le cœur la refait, mais le modèle doit rendre des vecteurs
  cohérents entre eux.

Les deux bibliothèques nécessaires — `onnxruntime` et `tokenizers` — sont compilées.
C'est l'exception assumée par la décision 0019 : elles vivent dans ce plugin, jamais
dans le cœur, et leur absence n'empêche ni PRISME de démarrer, ni ce plugin de se
charger — seul le fournisseur se déclare indisponible.
"""
import threading
from pathlib import Path

MAX_JETONS = 512           # au-dela, e5 tronque de toute facon
PREFIXES = {"requete": "query: ", "passage": "passage: "}


class MoteurIndisponible(RuntimeError):
    pass


def dependances():
    """(ok, message). Aucune importation au chargement du plugin : on sonde."""
    manquantes = []
    for module, paquet in (("onnxruntime", "onnxruntime"), ("tokenizers", "tokenizers")):
        try:
            __import__(module)
        except ImportError:
            manquantes.append(paquet)
    if manquantes:
        return False, ("Bibliothèques manquantes : %s. Installez-les avec "
                       "« pip install %s »." % (", ".join(manquantes), " ".join(manquantes)))
    return True, ""


class Moteur:
    """Charge le modèle une fois et le garde. Sûr en usage concurrent."""

    def __init__(self, dossier, prefixes=True, fils=None):
        self.dossier = Path(dossier)
        self.prefixes = prefixes
        self.fils = fils
        self._session = None
        self._tok = None
        self._dim = None
        self._entrees = ()
        self._verrou = threading.Lock()

    # ── Chargement ───────────────────────────────────────────────────────
    def charger(self):
        with self._verrou:
            if self._session is not None:
                return
            ok, message = dependances()
            if not ok:
                raise MoteurIndisponible(message)
            import onnxruntime
            from tokenizers import Tokenizer

            onnx = self.dossier / "model.onnx"
            tok = self.dossier / "tokenizer.json"
            for f in (onnx, tok):
                if not f.is_file():
                    raise MoteurIndisponible("Fichier manquant : %s" % f.name)

            options = onnxruntime.SessionOptions()
            if self.fils:
                options.intra_op_num_threads = int(self.fils)
            # Fournisseur CPU uniquement : le but est que ca tourne partout, pas vite.
            try:
                self._session = onnxruntime.InferenceSession(
                    str(onnx), sess_options=options, providers=["CPUExecutionProvider"])
            except Exception as e:                                    # noqa: BLE001
                raise MoteurIndisponible("Modèle ONNX illisible : %s" % str(e)[:200])
            self._tok = Tokenizer.from_file(str(tok))
            try:
                self._tok.enable_truncation(max_length=MAX_JETONS)
                self._tok.enable_padding()
            except Exception:                                         # noqa: BLE001
                pass                                                  # tokeniseur sans ces reglages
            self._entrees = tuple(e.name for e in self._session.get_inputs())

    def dimension(self):
        if self._dim is None:
            self._dim = len(self.encoder(["sonde"], role="passage")[0])
        return self._dim

    # ── Inference ────────────────────────────────────────────────────────
    def encoder(self, textes, role="passage"):
        """[[float]] : un vecteur par texte, moyenne masquée puis normalisée."""
        self.charger()
        textes = list(textes)
        if not textes:
            return []
        if self.prefixes:
            prefixe = PREFIXES.get(role, PREFIXES["passage"])
            textes = [prefixe + (t or "") for t in textes]

        lots = self._tok.encode_batch(textes)
        ids = [e.ids[:MAX_JETONS] for e in lots]
        masques = [e.attention_mask[:MAX_JETONS] for e in lots]
        largeur = max(len(x) for x in ids)
        # Remplissage explicite : certains tokeniseurs n'ont pas de jeton de padding
        # declare, et un lot bancal fait echouer ONNX avec un message illisible.
        ids = [x + [0] * (largeur - len(x)) for x in ids]
        masques = [m + [0] * (largeur - len(m)) for m in masques]

        entrees = {}
        if "input_ids" in self._entrees:
            entrees["input_ids"] = _int64(ids)
        if "attention_mask" in self._entrees:
            entrees["attention_mask"] = _int64(masques)
        if "token_type_ids" in self._entrees:
            entrees["token_type_ids"] = _int64([[0] * largeur for _ in ids])
        if not entrees:
            raise MoteurIndisponible(
                "Entrées du modèle inattendues : %s" % ", ".join(self._entrees))

        try:
            sortie = self._session.run(None, entrees)[0]
        except Exception as e:                                        # noqa: BLE001
            raise MoteurIndisponible("Inférence impossible : %s" % str(e)[:200])
        return [_moyenne_masquee(sortie[i], masques[i]) for i in range(len(ids))]


def _int64(matrice):
    import numpy                                                      # fourni par onnxruntime
    return numpy.asarray(matrice, dtype=numpy.int64)


def _moyenne_masquee(jetons, masque):
    """Moyenne des vecteurs de jetons, sans compter le remplissage, puis normalisée.

    C'est l'agrégation attendue par e5. Prendre le premier jeton (CLS) ou une moyenne
    non masquée donne des vecteurs plausibles mais nettement moins bons — et rien ne
    le signale.
    """
    import math

    dim = len(jetons[0])
    somme = [0.0] * dim
    compte = 0
    for i, garde in enumerate(masque):
        if not garde or i >= len(jetons):
            continue
        compte += 1
        ligne = jetons[i]
        for d in range(dim):
            somme[d] += float(ligne[d])
    if compte == 0:
        return [0.0] * dim
    moyenne = [x / compte for x in somme]
    norme = math.sqrt(sum(x * x for x in moyenne))
    return [x / norme for x in moyenne] if norme > 0 else moyenne
