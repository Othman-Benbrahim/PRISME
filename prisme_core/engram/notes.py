"""Ecriture des notes d'une source importee (docs/decisions/0014 et 0016).

Une note par source ; au-dela d'un seuil, la source est repartie en parties
reliees par une note sommaire. Chaque passage porte une ancre de bloc Obsidian
(`^p-xxxxxxxx`) : c'est la que vit son identifiant, dans le vault, et non dans
une base a part. Les passages disparus de la source sont conserves en fin de
note, dans un encadre rouge.
"""
import re
from pathlib import Path

SEUIL_PARTIE = 200_000          # caracteres ; reglable dans la configuration
TITRE_ARCHIVE = "Passages retirés de la source"
_ANCRE = re.compile(r"^\^(p-[0-9a-z]{8})\s*$", re.M)
_BLOC = re.compile(r"(?:^|\n)##\s+(?P<titre>[^\n]*)\n(?P<corps>.*?)\n\^(?P<id>p-[0-9a-z]{8})\s*(?=\n|$)",
                   re.S)


def slug(texte, defaut="source"):
    propre = re.sub(r"[^\w\-. ]", "", (texte or "").strip(), flags=re.UNICODE)
    propre = re.sub(r"\s+", "-", propre).strip("-.")[:60]
    return propre or defaut


def passages_existants(contenu):
    """Relit les passages deja ecrits dans une note : [{id, titre, texte, empreinte}]."""
    import hashlib
    corps, _, archive = contenu.partition(f"## {TITRE_ARCHIVE}")
    out = []
    for m in _BLOC.finditer(corps):
        titre = m.group("titre").strip()
        texte = m.group("corps").strip()
        # le titre porte « Rôle — date » : l'empreinte ne garde que le role
        role = titre.split("—")[0].strip()
        out.append({"id": m.group("id"), "titre": role, "texte": texte,
                    "empreinte": hashlib.sha256(f"{role}\n{texte}".encode("utf-8")).hexdigest()[:16]})
    return out


def archives_existantes(contenu):
    """Passages deja archives, pour ne pas les perdre a la reecriture."""
    _, sep, archive = contenu.partition(f"## {TITRE_ARCHIVE}")
    if not sep:
        return []
    blocs = []
    for bloc in re.split(r"\n(?=> \[!danger\])", archive):
        if bloc.strip().startswith("> [!danger]"):
            ancre = _ANCRE.search(bloc.replace("> ", ""))
            blocs.append({"bloc": bloc.rstrip(), "id": ancre.group(1) if ancre else ""})
    return blocs


def rendre_passage(attribution):
    p = attribution["passage"]
    entete = p.titre or "Passage"
    if p.date:
        entete += f" — {p.date}"
    return f"## {entete}\n\n{p.texte.strip()}\n\n^{attribution['id']}\n"


def rendre_archive(retire, date_retrait, version_source):
    """Encadre rouge, affiche en rouge par Obsidian comme par PRISME."""
    lignes = [f"> [!danger] Retiré de la source — {date_retrait}"]
    lignes += [f"> {l}" if l.strip() else ">" for l in retire["texte"].strip().split("\n")]
    lignes.append(f"> ^{retire['id']}")
    lignes.append(f"> <!-- version de la source : {version_source[:12]} -->")
    return "\n".join(lignes) + "\n"

def composer(titre, entete_yaml, attributions, archives, sommaire=""):
    corps = [f"# {titre}\n"]
    if sommaire:
        corps.append(sommaire)
    corps += [rendre_passage(a) for a in attributions]
    if archives:
        corps.append(f"## {TITRE_ARCHIVE}\n")
        corps += [a["bloc"] if isinstance(a, dict) and "bloc" in a else a for a in archives]
    return entete_yaml + "\n".join(corps).rstrip() + "\n"


def repartir(attributions, seuil=SEUIL_PARTIE):
    """Decoupe en parties sans jamais couper un passage."""
    total = sum(len(a["passage"].texte) for a in attributions)
    if total <= seuil:
        return [attributions]
    parties, courante, taille = [], [], 0
    for a in attributions:
        long = len(a["passage"].texte)
        if courante and taille + long > seuil:
            parties.append(courante)
            courante, taille = [], 0
        courante.append(a)
        taille += long
    if courante:
        parties.append(courante)
    return parties


def noms_parties(base, nombre):
    if nombre == 1:
        return [f"{base}.md"]
    return [f"{base}-partie-{i:02d}.md" for i in range(1, nombre + 1)]


def sommaire_markdown(base, noms, comptes_par_partie):
    lignes = ["Cette source est répartie en plusieurs parties :\n"]
    for nom, n in zip(noms, comptes_par_partie):
        lignes.append(f"- [[{Path(nom).stem}]] — {n} passage(s)")
    return "\n".join(lignes) + "\n"
