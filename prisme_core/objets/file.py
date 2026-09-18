"""File de validation, hors du vault (docs/decisions/0017).

Ce que l'IA ou un agent propose attend ici. Rien n'entre dans le vault sans un
accord explicite. Un rejet est mémorisé avec sa raison : l'IA le relit avant de
proposer à nouveau, pour qu'un refus ponctuel ne soit pas pris pour une règle
générale, et pour ne pas reproposer dix fois la même chose.
"""
import json
import time

PLAFOND_PAR_ORIGINE = 500          # une file ingérable finit abandonnée (0021)
FICHIER = "file.json"


def _fichier():
    from ..paths import DATA_DIR
    d = DATA_DIR / "objets"
    d.mkdir(parents=True, exist_ok=True)
    return d / FICHIER


def _lire():
    try:
        data = json.loads(_fichier().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault("entrees", [])
    data.setdefault("rejets", {})
    return data


def _ecrire(data):
    _fichier().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def ajouter(entree):
    """Dépose une proposition. Renvoie l'entrée telle qu'enregistrée, ou None.

    None signifie : déjà en file, déjà rejetée, ou plafond atteint pour cette origine.
    L'appelant n'a pas à tenir ces comptes.
    """
    cle = (entree.get("cle") or "").strip()
    if not cle:
        return None
    data = _lire()
    if cle in data["rejets"]:
        return None
    if any(e["cle"] == cle for e in data["entrees"]):
        return None
    origine = entree.get("origine") or "inconnue"
    if sum(1 for e in data["entrees"] if e.get("origine") == origine) >= PLAFOND_PAR_ORIGINE:
        return None
    enregistree = {
        "cle": cle,
        "brut": entree.get("brut", ""),
        "genre": entree.get("genre", "url"),
        "titre": entree.get("titre", ""),
        "origine": origine,
        "note": entree.get("note", ""),
        "indice": entree.get("indice", ""),
        "motif": entree.get("motif", ""),
        "propose_le": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    data["entrees"].append(enregistree)
    _ecrire(data)
    return enregistree


def lister(origine=None):
    entrees = _lire()["entrees"]
    return [e for e in entrees if not origine or e.get("origine") == origine]


def par_cle(cle):
    return next((e for e in _lire()["entrees"] if e["cle"] == cle), None)


def retirer(cle):
    """Sort une entrée de la file sans la mémoriser comme rejet (cas d'une acceptation)."""
    data = _lire()
    reste = [e for e in data["entrees"] if e["cle"] != cle]
    if len(reste) == len(data["entrees"]):
        return None
    sortie = next(e for e in data["entrees"] if e["cle"] == cle)
    data["entrees"] = reste
    _ecrire(data)
    return sortie


def rejeter(cle, raison=""):
    """Rejette une proposition et mémorise le refus, avec sa raison si elle est donnée."""
    data = _lire()
    entree = next((e for e in data["entrees"] if e["cle"] == cle), None)
    data["entrees"] = [e for e in data["entrees"] if e["cle"] != cle]
    data["rejets"][cle] = {
        "raison": (raison or "").strip(),
        "titre": (entree or {}).get("titre", ""),
        "brut": (entree or {}).get("brut", ""),
        "rejete_le": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    _ecrire(data)
    return data["rejets"][cle]


def rejets():
    return _lire()["rejets"]


def oublier_rejet(cle):
    """Lève un refus : la référence pourra être proposée à nouveau."""
    data = _lire()
    parti = data["rejets"].pop(cle, None)
    if parti is not None:
        _ecrire(data)
    return parti


def raisons_connues(limite=40):
    """Les refus déjà exprimés, à relire avant de proposer (révision de 0017)."""
    out = []
    for cle, r in _lire()["rejets"].items():
        if r.get("raison"):
            out.append({"cle": cle, "raison": r["raison"], "titre": r.get("titre", "")})
    return out[:limite]


def vider():
    _ecrire({"entrees": [], "rejets": _lire()["rejets"]})
