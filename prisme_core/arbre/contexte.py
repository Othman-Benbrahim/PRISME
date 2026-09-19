"""Assemblage du contexte envoyé au modèle, et mesure de ce qu'il coûte.

L'économie promise par la décision 0029 ne vient pas d'envoyer moins de texte au
hasard : elle vient d'envoyer **une carte** — les titres et les relations — avec
seulement les notes retenues, au lieu d'une pluie d'extraits qui se répètent.

La décision exige de mesurer plutôt que de supposer. `comparer()` chiffre donc, sur la
même question, ce que coûterait la recherche plate et ce que coûte l'arbre.
"""
from pathlib import Path

from ..vault import safe_path
from .parcours import MAX_PAR_NOTE


def _lire(chemin):
    try:
        return safe_path(chemin).read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return ""


def carte(noeuds):
    """La carte des relations, en quelques lignes : c'est ce qui remplace le volume.

    Un modèle qui voit « B est cité par A, et cite C » raisonne sur la structure sans
    qu'on lui envoie A et C en entier.
    """
    par_chemin = {n["chemin"]: n for n in noeuds}
    lignes = []
    for n in sorted(noeuds, key=lambda x: (x["niveau"], -x["score"])):
        indent = "  " * n["niveau"]
        marque = "" if n["retenu"] else "  (non joint)"
        parent = par_chemin.get(n["parent"])
        relation = ""
        if parent is not None:
            relation = " — %s" % n["motif"]
        lignes.append("%s- %s%s%s" % (indent, Path(n["chemin"]).stem, relation, marque))
    return "\n".join(lignes)


def assembler(arbre, retenus=None):
    """(texte du contexte, détail par note). `retenus` remplace la sélection du budget."""
    noeuds = arbre["noeuds"]
    choisis = set(retenus if retenus is not None else arbre["retenus"])
    morceaux = ["## Carte des notes et de leurs relations\n", carte(noeuds), "\n"]
    detail = []
    for n in sorted(noeuds, key=lambda x: -x["score"]):
        if n["chemin"] not in choisis:
            continue
        texte = _lire(n["chemin"])
        tronque = len(texte) > MAX_PAR_NOTE
        texte = texte[:MAX_PAR_NOTE]
        morceaux.append("\n## %s\n" % Path(n["chemin"]).stem)
        morceaux.append("_%s_\n" % n["motif"])
        morceaux.append(texte)
        if tronque:
            morceaux.append("\n_(note tronquée)_")
        detail.append({"chemin": n["chemin"], "nom": n["nom"], "motif": n["motif"],
                       "caracteres": len(texte), "tronquee": tronque})
    contexte = "\n".join(morceaux)
    return contexte, detail


def comparer(index, question, arbre, cfg=None, racine=None):
    """Ce que coûterait la recherche plate, face à ce que coûte l'arbre.

    Deux comparaisons, parce qu'une seule mentirait :

    - contre la recherche plate **non bornée**, l'arbre paraît très économe — mais ce
      n'est que l'effet du budget, et n'importe quel plafond ferait autant ;
    - contre la même recherche plate **tronquée au même budget**, l'arbre coûte un peu
      *plus*. C'est la comparaison honnête, et c'est celle qui dit ce que l'arbre apporte
      vraiment : `apport_liens`, les notes retenues qu'aucun score n'avait remontées.

    La décision 0029 exigeait de mesurer plutôt que de supposer ; cette fonction est
    l'instrument, et son résultat a corrigé la justification de l'étape.
    """
    from ..vecteurs.recherche import hybride

    resultats, _info = hybride(index, question, limit_files=40, racine=racine, cfg=cfg)
    plat, tronque, n_tronque = 0, 0, 0
    for r in resultats:
        cout = min(len(_lire(r["path"])), MAX_PAR_NOTE)
        plat += cout
        if tronque + cout <= arbre["budget"]:
            tronque += cout
            n_tronque += 1
    contexte, _detail = assembler(arbre)
    vus = {r["path"] for r in resultats[:n_tronque]}
    return {"plat_caracteres": plat, "plat_notes": len(resultats),
            "plat_tronque_caracteres": tronque, "plat_tronque_notes": n_tronque,
            "arbre_caracteres": len(contexte), "arbre_notes": len(arbre["retenus"]),
            "carte_caracteres": len(carte(arbre["noeuds"])),
            # ce que l'arbre apporte et que le plat, à budget égal, n'aurait pas eu
            "apport_liens": len(set(arbre["retenus"]) - vus),
            "gain": (plat - len(contexte)) if plat else 0,
            "gain_a_budget_egal": tronque - len(contexte)}


CONSIGNE = """Tu réponds à partir des notes ci-dessous, et d'elles seules.

La carte au début dit comment ces notes sont reliées : qui cite qui. Utilise-la — une
relation entre deux notes est souvent la réponse, pas seulement leur contenu.

Règles :
- cite les notes sur lesquelles tu t'appuies, par leur nom, entre crochets doubles ;
- si les notes ne suffisent pas à répondre, dis-le au lieu de combler ;
- signale une contradiction entre deux notes plutôt que de choisir en silence."""
