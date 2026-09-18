"""Journal des appels d'agent (docs/decisions/0018).

Un agent agit sans que tu le regardes : ce que tu peux relire après coup est la seule
garantie qui reste. Chaque appel laisse une ligne — qui, quand, quoi, avec quel
résultat. Le journal survit à la révocation de la clé, sinon effacer sa clé
effacerait sa trace.

Format : un objet JSON par ligne (JSONL), pour qu'une ligne corrompue n'emporte pas
le fichier et qu'on puisse le lire avec n'importe quel outil.
"""
import json
import os
import threading
import time

MAX_LIGNES = 5000          # au-delà, la moitié la plus ancienne part dans .1
FICHIER = "journal.jsonl"
_VERROU = threading.Lock()


def _fichier():
    from ..paths import DATA_DIR
    d = DATA_DIR / "agents"
    d.mkdir(parents=True, exist_ok=True)
    return d / FICHIER


def consigner(ident, nom, methode, chemin, statut, detail=""):
    """Ajoute une ligne. Un journal en panne ne doit jamais faire échouer l'appel."""
    ligne = {
        "le": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "cle": ident or "-",
        "agent": nom or "-",
        "methode": methode,
        "chemin": chemin,
        "statut": statut,
        "detail": (detail or "")[:300],
    }
    try:
        with _VERROU:
            f = _fichier()
            with open(f, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            _rogner(f)
    except OSError:
        pass
    return ligne


def _rogner(f):
    """Garde le journal borné : au-delà du plafond, l'ancienne moitié passe en .1."""
    try:
        if f.stat().st_size < 200 * MAX_LIGNES:
            return                                  # estimation grossière, évite de tout relire
        lignes = f.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lignes) <= MAX_LIGNES:
            return
        garde = lignes[len(lignes) // 2:]
        archive = f.with_suffix(".jsonl.1")
        if archive.exists():
            os.replace(archive, f.with_suffix(".jsonl.2"))
        os.replace(f, archive)
        f.write_text("\n".join(garde) + "\n", encoding="utf-8")
    except OSError:
        pass


def lire(limite=200, cle=None):
    """Les dernières lignes, la plus récente d'abord."""
    try:
        brut = _fichier().read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out = []
    for ligne in reversed(brut):
        if not ligne.strip():
            continue
        try:
            obj = json.loads(ligne)
        except ValueError:
            continue                                # une ligne abîmée n'emporte pas le reste
        if cle and obj.get("cle") != cle:
            continue
        out.append(obj)
        if len(out) >= limite:
            break
    return out


def comptes():
    """Résumé par clé, pour l'interface."""
    par_cle = {}
    for obj in lire(limite=MAX_LIGNES):
        c = par_cle.setdefault(obj.get("cle", "-"), {"appels": 0, "refus": 0})
        c["appels"] += 1
        if int(obj.get("statut", 200)) >= 400:
            c["refus"] += 1
    return par_cle


def vider():
    try:
        _fichier().unlink()
    except OSError:
        pass
