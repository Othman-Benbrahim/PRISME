"""Les 16 cartes, chargées depuis `cartes.json` — jamais recopiées dans du code.

`references/cards.md` du dépôt NEXUS-ARCHÊ fait plus de 20 000 caractères : porté dans
un module Python, il ferait sauter la règle « aucun fichier monolithique » (0005) à lui
seul. Les données vivent donc dans un fichier de données, et la fidélité aux références
se vérifie par comparaison plutôt que par relecture.
"""
import json
from pathlib import Path

FICHIER = Path(__file__).with_name("cartes.json")
_CACHE = {}


def _charge():
    if not _CACHE:
        # encoding explicite : les 16 glyphes sont hors cp1252, et la machine cible
        # est Windows. Sans ce paramètre, la lecture dépend de la locale.
        d = json.loads(FICHIER.read_text(encoding="utf-8"))
        _CACHE["cartes"] = d["cartes"]
        _CACHE["par_id"] = {c["id"]: c for c in d["cartes"]}
    return _CACHE


def toutes():
    return list(_charge()["cartes"])


def par_id(ident):
    return _charge()["par_id"].get(ident)


def existe(ident):
    return ident in _charge()["par_id"]


def glyphes():
    return {c["glyphe"]: c["id"] for c in toutes()}


def distinctions(ident):
    """Les critères « À ne pas confondre avec » d'une carte."""
    c = par_id(ident)
    return list(c["distinctions"]) if c else []


def questions_entre(a, b):
    """Les critères qui séparent deux cartes, dans les deux sens.

    C'est ce qui est posé à l'AUTEUR quand deux cartes restent en lice — pas au modèle.
    Le critère est déjà écrit dans les références sous forme de question ; on ne le
    reformule pas.
    """
    out = []
    for source, cible in ((a, b), (b, a)):
        for d in distinctions(source):
            if d["autre"] == cible and d["critere"]:
                out.append({"entre": [source, cible], "critere": d["critere"],
                            "explication": d["explication"]})
    return out


def confusions(ident):
    """Les cartes avec lesquelles celle-ci se confond, d'après les références."""
    return [d["autre"] for d in distinctions(ident)]
