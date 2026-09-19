"""Trousseau des clés d'agent (docs/decisions/0018).

Une clé par agent, affichée **une seule fois** : seule son empreinte est conservée,
si bien qu'un vol du fichier de profil ne donne aucune clé utilisable. Révocable à
tout moment, avec des droits par clé.

Droits :

- `lecture` — chercher dans le vault, lire une note, lister les objets Source ;
- `proposition` — déposer dans la file de validation d'E5, jamais dans le vault ;
- `ecriture` — écrire directement une note ; **accordé au cas par cas**, jamais par
  défaut, comme la décision 0018 l'exige ;
- `toutes_racines` — voir les racines secondaires du vault. Sans lui, une clé ne connaît
  que la racine principale, quelles que soient les racines déclarées (0028).
"""
import hashlib
import hmac
import json
import re
import secrets as aleatoire
import threading
import time

PREFIXE = "prisme-"
DROITS = ("lecture", "proposition", "ecriture", "toutes_racines")
DROITS_DEFAUT = ("lecture", "proposition")
FICHIER = "cles.json"
_VERROU = threading.Lock()

_NOM = re.compile(r"^[\w \-.']{2,60}$", re.UNICODE)


class CleInvalide(ValueError):
    pass


def _fichier():
    from ..paths import DATA_DIR
    d = DATA_DIR / "agents"
    d.mkdir(parents=True, exist_ok=True)
    return d / FICHIER


def _lire():
    try:
        return json.loads(_fichier().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _ecrire(data):
    _fichier().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def empreinte(cle):
    """SHA-256 de la clé.

    Pas de KDF lent ici, et c'est délibéré : la clé fait 256 bits d'aléa, elle n'est
    ni devinable ni attaquable par dictionnaire. Un PBKDF2 sur chaque requête ne
    protégerait de rien et coûterait une latence à chaque appel d'agent.
    """
    return hashlib.sha256((cle or "").encode("utf-8")).hexdigest()


def _indice(cle):
    """De quoi reconnaître une clé dans la liste sans pouvoir la reconstituer."""
    return cle[:len(PREFIXE) + 4] + "…" + cle[-2:]


def creer(nom, droits=DROITS_DEFAUT):
    """Crée une clé. Renvoie (identifiant, clé en clair) — la clé n'est plus lisible ensuite."""
    nom = (nom or "").strip()
    if not _NOM.match(nom):
        raise CleInvalide("Nom d'agent invalide : 2 à 60 caractères, sans ponctuation exotique")
    droits = _valider_droits(droits)
    cle = PREFIXE + aleatoire.token_urlsafe(32)
    with _VERROU:
        data = _lire()
        if any(v["nom"].lower() == nom.lower() and not v.get("revoquee_le") for v in data.values()):
            raise CleInvalide("Une clé active porte déjà ce nom")
        ident = "ag-" + aleatoire.token_hex(4)
        while ident in data:
            ident = "ag-" + aleatoire.token_hex(4)
        data[ident] = {
            "nom": nom,
            "empreinte": empreinte(cle),
            "indice": _indice(cle),
            "droits": droits,
            "creee_le": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "derniere_utilisation": "",
            "appels": 0,
            "revoquee_le": "",
        }
        _ecrire(data)
    return ident, cle


def _valider_droits(droits):
    propres = [d for d in (droits or ()) if d in DROITS]
    if "lecture" not in propres:
        propres.insert(0, "lecture")        # sans lecture, une clé ne sert à rien
    return sorted(set(propres), key=DROITS.index)


def lister(avec_revoquees=True):
    out = []
    for ident, info in sorted(_lire().items(), key=lambda kv: kv[1].get("creee_le", "")):
        if not avec_revoquees and info.get("revoquee_le"):
            continue
        out.append({k: v for k, v in info.items() if k != "empreinte"} | {"id": ident})
    out.reverse()
    return out


def par_id(ident):
    info = _lire().get(ident)
    return ({k: v for k, v in info.items() if k != "empreinte"} | {"id": ident}) if info else None


def revoquer(ident):
    """Une clé révoquée n'est pas effacée : son historique reste lisible dans le journal."""
    with _VERROU:
        data = _lire()
        if ident not in data:
            raise CleInvalide("Clé inconnue : %s" % ident)
        if data[ident].get("revoquee_le"):
            raise CleInvalide("Clé déjà révoquée")
        data[ident]["revoquee_le"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _ecrire(data)
    return par_id(ident)


def oublier(ident):
    """Efface une clé révoquée du trousseau. Le journal, lui, garde la trace."""
    with _VERROU:
        data = _lire()
        info = data.get(ident)
        if info is None:
            raise CleInvalide("Clé inconnue : %s" % ident)
        if not info.get("revoquee_le"):
            raise CleInvalide("Révoquez la clé avant de l'oublier")
        data.pop(ident)
        _ecrire(data)
    return {"ok": True, "id": ident}


def changer_droits(ident, droits):
    """Accorde ou retire des droits. C'est ici que passe l'accord explicite pour l'écriture."""
    with _VERROU:
        data = _lire()
        if ident not in data:
            raise CleInvalide("Clé inconnue : %s" % ident)
        if data[ident].get("revoquee_le"):
            raise CleInvalide("Clé révoquée")
        data[ident]["droits"] = _valider_droits(droits)
        _ecrire(data)
    return par_id(ident)


def verifier(cle):
    """(identifiant, info) de la clé présentée, ou (None, raison) si elle est refusée."""
    cle = (cle or "").strip()
    if not cle:
        return None, "Clé absente"
    attendue = empreinte(cle)
    for ident, info in _lire().items():
        # compare_digest : le temps de comparaison ne dit rien sur l'empreinte visée.
        if hmac.compare_digest(info.get("empreinte", ""), attendue):
            if info.get("revoquee_le"):
                return None, "Clé révoquée le %s" % info["revoquee_le"]
            return ident, info
    return None, "Clé inconnue"


def marquer_utilisation(ident):
    with _VERROU:
        data = _lire()
        if ident in data:
            data[ident]["derniere_utilisation"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            data[ident]["appels"] = int(data[ident].get("appels", 0)) + 1
            _ecrire(data)


def origine(ident, info=None):
    """Étiquette de l'agent dans la file de validation : le plafond d'E5 devient par clé."""
    info = info or par_id(ident) or {}
    return "agent:%s" % (info.get("nom") or ident)
