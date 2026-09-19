"""Gestion du modèle local : découverte, téléchargement, vérification.

Deux façons de fournir un modèle, et la première est la plus sûre :

1. **Un dossier que vous avez déjà** — vous téléchargez le modèle vous-même, depuis la
   source de votre choix, et vous indiquez le dossier. PRISME ne fait que le lire.
2. **Un téléchargement depuis une URL** — pratique, mais c'est du code qui va chercher
   des dizaines de mégaoctets sur Internet : l'empreinte du fichier obtenu est affichée,
   et vous pouvez l'épingler pour que tout écart soit refusé ensuite.

Un modèle utilisable est un dossier contenant :

    model.onnx        le réseau, de préférence quantifié
    tokenizer.json    le tokeniseur, au format « tokenizers » de HuggingFace

`config.json` est lu s'il est là, pour connaître la dimension sans lancer le modèle.
"""
import hashlib
import json
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse

FICHIERS = ("model.onnx", "tokenizer.json")
MAX_OCTETS = 800 * 1024 * 1024        # un modele d'embeddings depasse rarement 500 Mo
MORCEAU = 1024 * 256


class ModeleInvalide(RuntimeError):
    pass


def valider_dossier(dossier):
    """(chemin, manquants). Ne lève pas : l'interface affiche ce qui manque."""
    d = Path(dossier).expanduser()
    if not d.is_dir():
        return None, list(FICHIERS)
    return d, [f for f in FICHIERS if not (d / f).is_file()]


def empreinte(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(MORCEAU), b""):
            h.update(bloc)
    return h.hexdigest()


def decrire(dossier):
    """Ce qu'on sait d'un dossier de modèle, sans rien charger."""
    d, manquants = valider_dossier(dossier)
    if d is None:
        return {"present": False, "manquants": manquants, "dossier": str(dossier or "")}
    info = {"present": not manquants, "manquants": manquants, "dossier": str(d)}
    onnx = d / "model.onnx"
    if onnx.is_file():
        info["taille"] = onnx.stat().st_size
        info["sha256"] = empreinte(onnx)
    cfg = d / "config.json"
    if cfg.is_file():
        try:
            brut = json.loads(cfg.read_text(encoding="utf-8"))
            info["dimension_annoncee"] = brut.get("hidden_size")
            info["architecture"] = (brut.get("architectures") or [None])[0]
        except (OSError, ValueError):
            pass
    return info


def _url_sure(url):
    p = urlparse(url or "")
    if p.scheme != "https":
        raise ModeleInvalide("Seules les URL https sont acceptées")
    if not p.netloc or "." not in p.netloc:
        raise ModeleInvalide("URL invalide : %s" % url)
    return url


def telecharger(url, destination, progression=None, attendu=None):
    """Télécharge un fichier en le vérifiant. `progression(faits, total)` est optionnel.

    Le fichier est écrit à côté sous un nom temporaire puis renommé : une coupure de
    réseau ne laisse jamais un modèle à moitié écrit qui semblerait valide.
    """
    import requests as http

    _url_sure(url)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partiel = destination.with_suffix(destination.suffix + ".partiel")
    h = hashlib.sha256()
    faits = 0
    try:
        with http.get(url, stream=True, timeout=60) as r:
            if r.status_code != 200:
                raise ModeleInvalide("HTTP %d en téléchargeant %s" % (r.status_code, url))
            total = int(r.headers.get("content-length") or 0)
            if total > MAX_OCTETS:
                raise ModeleInvalide("Fichier trop volumineux : %.0f Mo" % (total / 1e6))
            with open(partiel, "wb") as f:
                for bloc in r.iter_content(MORCEAU):
                    if not bloc:
                        continue
                    faits += len(bloc)
                    if faits > MAX_OCTETS:
                        raise ModeleInvalide("Fichier trop volumineux (dépasse %d Mo)"
                                             % (MAX_OCTETS // 1_000_000))
                    h.update(bloc)
                    f.write(bloc)
                    if progression:
                        progression(faits, total)
    except ModeleInvalide:
        partiel.unlink(missing_ok=True)
        raise
    except Exception as e:                                            # noqa: BLE001
        partiel.unlink(missing_ok=True)
        raise ModeleInvalide("Téléchargement interrompu : %s: %s" % (type(e).__name__, str(e)[:160]))

    obtenue = h.hexdigest()
    if attendu and obtenue != attendu:
        partiel.unlink(missing_ok=True)
        raise ModeleInvalide(
            "Empreinte inattendue : %s reçue, %s attendue. Fichier écarté." % (obtenue[:16], attendu[:16]))
    shutil.move(str(partiel), str(destination))
    return {"chemin": str(destination), "octets": faits, "sha256": obtenue,
            "le": time.strftime("%Y-%m-%dT%H:%M:%S")}


def installer(urls, dossier, progression=None, empreintes=None):
    """Télécharge les fichiers d'un modèle dans `dossier`. `urls` : {nom: url}."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    empreintes = empreintes or {}
    rapport = {}
    for nom in FICHIERS:
        if nom not in urls:
            raise ModeleInvalide("URL manquante pour %s" % nom)
        rapport[nom] = telecharger(
            urls[nom], dossier / nom,
            progression=(lambda f, t, n=nom: progression(n, f, t)) if progression else None,
            attendu=empreintes.get(nom))
    return rapport
