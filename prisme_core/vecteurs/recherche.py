"""Recherche sémantique et fusion avec la recherche lexicale (docs/decisions/0019).

La règle qui compte : **la recherche ne tombe jamais.** Si le fournisseur est absent,
mal configuré, en panne ou simplement lent, on rend le résultat FTS5 seul et on le dit
dans la réponse. Une recherche dégradée vaut mieux qu'une recherche en erreur.
"""
from ..index import search as lexical
from . import quantification as quant
from .contrat import VecteurIndisponible
from .magasin import magasin_pour
from .vectorisation import fournisseur_configure

PLAFOND_SEGMENTS = 600

# Une recherche par mots qui ne trouve rien le dit. Une recherche par le sens, elle,
# rend toujours le moins mauvais candidat : sans plancher, chercher « zèbre » dans un
# vault qui n'en parle pas remonterait quarante notes au hasard. Deux coupes :
SEUIL_COSINUS = 0.30       # en dessous, c'est du bruit — dépend du modèle, réglable
RATIO_QUEUE = 0.50         # et on écarte la queue trop distante du meilleur résultat


def seuil_configure(cfg=None):
    from ..config import rd_cfg
    try:
        return float((cfg or rd_cfg()).get("emb_seuil") or SEUIL_COSINUS)
    except (TypeError, ValueError):
        return SEUIL_COSINUS


def vecteur_de_requete(texte, cfg=None):
    fournisseur = fournisseur_configure(cfg)
    if fournisseur is None:
        raise VecteurIndisponible("Recherche sémantique désactivée")
    # role « requete » : e5 et consorts encodent une question autrement qu un passage
    vecteurs = fournisseur.vectoriser_role([texte], role="requete")
    return quant.normaliser(vecteurs[0]), fournisseur


def semantique(texte, cfg=None, combien=PLAFOND_SEGMENTS):
    """[(sha256 de segment, cosinus)] du plus proche au plus lointain.

    Deux étages : présélection binaire sur tout le magasin, puis cosinus exact sur les
    meilleurs candidats. Voir `quantification` pour les mesures.
    """
    magasin = magasin_pour()
    bits = magasin.bits()
    if not bits:
        raise VecteurIndisponible("Aucun vecteur : lancez la vectorisation dans les Paramètres")
    requete, fournisseur = vecteur_de_requete(texte, cfg)
    attendue = fournisseur.signature()
    presente = magasin.signature()
    if presente and presente != attendue:
        raise VecteurIndisponible(
            "Les vecteurs ont été calculés avec %s, le fournisseur actuel est %s — "
            "relancez la vectorisation." % (presente, attendue))

    bits_requete = quant.binariser(requete)
    candidats = quant.preselectionner(bits_requete, bits)
    classes = quant.classer(requete, magasin.flottants(candidats))
    if not classes:
        return []
    plancher = max(seuil_configure(cfg), classes[0][1] * RATIO_QUEUE)
    return [(sha, score) for sha, score in classes[:combien] if score >= plancher]


def _lignes_par_sha(index, shas, root_filter=None):
    """Retrouve les segments correspondants dans l'index, en un seul aller-retour."""
    if not shas:
        return {}
    scope_sql, scope_args = lexical._scope(root_filter)
    out = {}
    with index.read() as conn:
        for debut in range(0, len(shas), 400):
            tranche = shas[debut:debut + 400]
            marques = ",".join("?" * len(tranche))
            rows = conn.execute(
                "SELECT s.sha256, s.file_id, s.heading, s.start_line, substr(s.text, 1, 200) AS extrait, "
                "f.path, f.name, f.rel FROM segments s JOIN files f ON f.id = s.file_id "
                "WHERE s.sha256 IN (%s)" % marques + scope_sql,
                tranche + scope_args).fetchall()
            for r in rows:
                out.setdefault(r["sha256"], r)      # un meme texte peut apparaitre deux fois
    return out


def hybride(index, texte, limit_files=40, per_file=3, root_filter=None, cfg=None):
    """Fusion RRF de la recherche lexicale et de la recherche sémantique.

    Renvoie (résultats, info) où `info` dit quel mode a réellement servi — l'utilisateur
    doit toujours savoir ce qui a tourné (docs/decisions/0019).
    """
    info = {"mode": "lexical", "semantique": False, "repli": ""}

    lex_rows = lexical.segments_lexicaux(index, texte, limite=PLAFOND_SEGMENTS,
                                         root_filter=root_filter)
    rang_lexical = [r["sha256"] for r in lex_rows]

    try:
        sem = semantique(texte, cfg=cfg)
        rang_semantique = [sha for sha, _score in sem]
        info["semantique"] = True
        info["mode"] = "hybride"
    except VecteurIndisponible as e:
        rang_semantique = []
        info["repli"] = str(e)
    except Exception as e:                                            # noqa: BLE001
        rang_semantique = []
        info["repli"] = "%s: %s" % (type(e).__name__, str(e)[:160])

    if not rang_semantique:
        # Repli complet : on rend exactement ce que rendrait la recherche lexicale.
        return lexical.search(index, texte, limit_files=limit_files,
                              per_file=per_file + 1, root_filter=root_filter), info

    fusion = quant.fusionner(rang_lexical, rang_semantique)
    par_sha = {r["sha256"]: r for r in lex_rows}
    manquants = [sha for sha, _s in fusion if sha not in par_sha]
    par_sha.update(_lignes_par_sha(index, manquants, root_filter))

    ordonnes = [(sha, score) for sha, score in fusion if sha in par_sha]
    ordonnes = quant.diversifier(ordonnes, lambda e: par_sha[e[0]]["file_id"],
                                 par_groupe=per_file, total=limit_files * per_file)

    lexicaux = set(rang_lexical)
    semantiques = set(rang_semantique)
    resultats, par_fichier = [], {}
    for sha, score in ordonnes:
        r = par_sha[sha]
        entree = par_fichier.get(r["file_id"])
        if entree is None:
            if len(resultats) >= limit_files:
                continue
            entree = {"path": r["path"], "name": r["name"], "rel": r["rel"],
                      "score": round(score, 5), "matches": []}
            par_fichier[r["file_id"]] = entree
            resultats.append(entree)
        if len(entree["matches"]) >= per_file:
            continue
        # D'ou vient ce passage : l'interface le signale, pour qu'un resultat trouve
        # par le sens seul ne passe pas pour une correspondance de mots.
        if sha in lexicaux and sha in semantiques:
            origine = "les deux"
        elif sha in semantiques:
            origine = "sens"
        else:
            origine = "mots"
        entree["matches"].append({
            "line": r["start_line"],
            "heading": r["heading"],
            "text": " ".join((r["extrait"] or "").split()),
            "origine": origine,
        })
    return resultats, info
