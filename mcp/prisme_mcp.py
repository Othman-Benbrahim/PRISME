#!/usr/bin/env python3
"""Adaptateur MCP pour PRISME — traduit MCP vers `/api/v1/` (docs/decisions/0032).

Ce fichier ne fait **aucune** logique métier. Il parle MCP sur l'entrée et la sortie
standard, et rappelle PRISME en HTTP local avec une clé d'agent. Toute la sécurité —
authentification, droits par clé, bornage aux racines, journal, file de validation —
reste dans PRISME, où elle est déjà testée. Un adaptateur qui referait ces contrôles
lui-même finirait par diverger, et diverger d'une garde de sécurité, c'est la perdre.

Conséquence voulue : ce script est jetable. Le remplacer ne change rien à ce qu'un
agent a le droit de faire.

**Bibliothèque standard uniquement.** Il est lancé par le client MCP avec le Python
qu'il trouve, pas par PRISME : exiger une dépendance ici, c'est exiger une installation
de la part de quelqu'un qui voulait juste coller un bloc de configuration.

Configuration (le bouton « Agents » de PRISME la produit toute faite) :

    {
      "mcpServers": {
        "prisme": {
          "command": "python",
          "args": ["C:/chemin/vers/prisme_mcp.py"],
          "env": {"PRISME_URL": "http://127.0.0.1:5000", "PRISME_CLE": "prisme-…"}
        }
      }
    }
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

VERSION = "1.0.1"
PROTOCOLE = "2024-11-05"          # version du protocole MCP annoncée à l'initialisation
DELAI = 30                        # secondes ; une recherche dans un gros vault prend son temps

# ── Encodage des flux : UTF-8, explicitement ────────────────────────────
# MCP transporte du JSON en UTF-8. Python, lui, ouvre stdin/stdout avec l'encodage du
# système : cp1252 sous Windows. Un vault français y passe encore, mais pas les flèches
# `→` et `←` des motifs de l'arbre : `sys.stdout.write` lève un UnicodeEncodeError, la
# réponse ne part jamais, et le client voit une session muette sans rien pour comprendre.
#
# `newline=""` en plus : en mode texte, Windows traduit `\n` en `\r\n`, et le protocole
# se lit ligne à ligne. On écrit nos fins de ligne nous-mêmes.
for _flux, _erreurs in ((sys.stdin, "replace"), (sys.stdout, "strict"), (sys.stderr, "replace")):
    try:
        _flux.reconfigure(encoding="utf-8", errors=_erreurs,
                          **({"newline": ""} if _flux is not sys.stdin else {}))
    except (AttributeError, ValueError):        # flux remplacé par un test, ou déjà figé
        pass

URL = (os.environ.get("PRISME_URL") or "http://127.0.0.1:5000").rstrip("/")
CLE = os.environ.get("PRISME_CLE") or ""


# ── Journal ─────────────────────────────────────────────────────────────
def trace(message):
    """La sortie standard porte le protocole : tout le reste part sur l'erreur standard.

    Un `print` égaré dans stdout casse la session MCP sans message lisible. C'est le
    piège classique de ce genre d'adaptateur, d'où cette fonction plutôt que `print`.
    """
    print("[prisme-mcp] %s" % message, file=sys.stderr, flush=True)


# ── Appel de PRISME ─────────────────────────────────────────────────────
class Souci(Exception):
    """Un problème à rendre à l'agent en texte clair, pas une trace de pile."""


def appeler(methode, chemin, params=None, corps=None):
    url = URL + chemin
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
    donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
    requete = urllib.request.Request(url, data=donnees, method=methode)
    requete.add_header("X-Prisme-Cle", CLE)
    if donnees is not None:
        requete.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse:
            return json.loads(reponse.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        # PRISME répond en JSON même sur erreur : on rend SON message, pas le nôtre.
        try:
            detail = json.loads(e.read().decode("utf-8")).get("error") or str(e)
        except Exception:                                        # noqa: BLE001
            detail = str(e)
        if e.code in (401, 403):
            raise Souci("PRISME a refusé la clé ou le droit : %s" % detail)
        raise Souci("PRISME a répondu %d : %s" % (e.code, detail))
    except urllib.error.URLError as e:
        raise Souci(
            "PRISME ne répond pas sur %s (%s). Lancez PRISME, puis réessayez : "
            "l'adaptateur ne fait que lui parler, il ne peut pas travailler sans lui."
            % (URL, e.reason))
    except (TimeoutError, OSError) as e:
        raise Souci("PRISME n'a pas répondu en %d s (%s)." % (DELAI, e))


# ── Les outils exposés ──────────────────────────────────────────────────
# Chaque entrée : description vue par l'agent, schéma d'entrée, et la traduction.
# La description compte autant que le code : c'est elle qui décide si l'agent choisit
# le bon outil. « chercher » et « arbre » se ressemblent — il faut dire quand prendre
# lequel, sinon l'agent prendra toujours le premier.

def _texte(valeur):
    """Le résultat, en texte, pour l'agent.

    `ensure_ascii=False` n'est pas cosmétique : sans lui, chaque accent devient `\\uXXXX`,
    six caractères au lieu d'un, sur un vault en français. Et pas d'indentation — un
    modèle lit le JSON compact aussi bien, et E13 a assez montré ce que coûte le volume.
    """
    if isinstance(valeur, str):
        return valeur
    return json.dumps(valeur, ensure_ascii=False)


OUTILS = [
    {
        "name": "prisme_notes",
        "description": "Liste les notes .md du vault avec leur chemin et leur taille. "
                       "Utile pour se repérer ; pour trouver quelque chose, préférer "
                       "prisme_chercher ou prisme_arbre.",
        "inputSchema": {"type": "object", "properties": {}},
        "appel": lambda a: appeler("GET", "/api/v1/notes"),
    },
    {
        "name": "prisme_lire",
        "description": "Lit une note du vault, avec sa provenance. Le chemin est celui "
                       "rendu par les autres outils.",
        "inputSchema": {
            "type": "object",
            "properties": {"chemin": {"type": "string", "description": "Chemin de la note"}},
            "required": ["chemin"],
        },
        "appel": lambda a: appeler("GET", "/api/v1/note", {"path": a.get("chemin", "")}),
    },
    {
        "name": "prisme_chercher",
        "description": "Recherche dans le vault : mots et sens, avec les passages trouvés. "
                       "À prendre quand on cherche UNE information précise. Pour comprendre "
                       "un sujet et les relations entre les notes, prendre prisme_arbre.",
        "inputSchema": {
            "type": "object",
            "properties": {"q": {"type": "string", "description": "Termes recherchés"}},
            "required": ["q"],
        },
        "appel": lambda a: appeler("GET", "/api/v1/recherche", {"q": a.get("q", "")}),
    },
    {
        "name": "prisme_arbre",
        "description": "Recherche en suivant les liens entre notes. Rend une carte des "
                       "relations (qui cite qui) et la liste des notes retenues. "
                       "À prendre pour explorer un sujet : retrouve des notes qu'aucun "
                       "score ne remonte, et montre comment elles s'articulent. "
                       "Rend les chemins, pas le contenu — lire ensuite ce qui sert.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "q": {"type": "string", "description": "Sujet exploré"},
                "depart": {"type": "string", "description": "Note de départ (facultatif)"},
            },
        },
        "appel": lambda a: appeler("GET", "/api/v1/arbre",
                                   {"q": a.get("q", ""), "depart": a.get("depart", "")}),
    },
    {
        "name": "prisme_sources",
        "description": "Liste les objets Source du vault — les références recensées et "
                       "leur statut de validation.",
        "inputSchema": {
            "type": "object",
            "properties": {"statut": {"type": "string", "description": "Filtre facultatif"}},
        },
        "appel": lambda a: appeler("GET", "/api/v1/objets", {"statut": a.get("statut", "")}),
    },
    {
        "name": "prisme_proposer",
        "description": "Dépose une référence dans la file de validation de l'auteur. "
                       "RIEN n'entre dans le vault : l'auteur relit et décide. "
                       "C'est la voie normale pour un agent qui a trouvé quelque chose.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "titre": {"type": "string"},
                "reference": {"type": "string", "description": "URL, DOI, arXiv, ISBN"},
                "note": {"type": "string", "description": "Note du vault concernée"},
                "motif": {"type": "string", "description": "Pourquoi cette référence"},
            },
            "required": ["titre"],
        },
        "appel": lambda a: appeler("POST", "/api/v1/proposer", corps={
            "titre": a.get("titre", ""), "reference": a.get("reference", ""),
            "note": a.get("note", ""), "motif": a.get("motif", "")}),
    },
    {
        "name": "prisme_ma_file",
        "description": "Ce que CET agent a déposé et qui attend encore la validation de "
                       "l'auteur. Ne montre pas les propositions des autres.",
        "inputSchema": {"type": "object", "properties": {}},
        "appel": lambda a: appeler("GET", "/api/v1/file"),
    },
    {
        "name": "prisme_ecrire",
        "description": "Écrit une note dans le vault. Demande le droit « ecriture », qui "
                       "n'est PAS accordé par défaut : sans lui, utiliser prisme_proposer. "
                       "La note est estampillée au nom de l'agent, et la version écrasée "
                       "reste récupérable.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chemin": {"type": "string", "description": "Chemin .md dans le vault"},
                "contenu": {"type": "string"},
            },
            "required": ["chemin", "contenu"],
        },
        "appel": lambda a: appeler("POST", "/api/v1/note", corps={
            "path": a.get("chemin", ""), "contenu": a.get("contenu", "")}),
    },
]
PAR_NOM = {o["name"]: o for o in OUTILS}


# ── Protocole MCP ───────────────────────────────────────────────────────
def repondre(ident, resultat=None, erreur=None):
    """Une réponse JSON-RPC. `ident` absent = notification : on ne répond pas."""
    if ident is None:
        return
    message = {"jsonrpc": "2.0", "id": ident}
    if erreur is not None:
        message["error"] = erreur
    else:
        message["result"] = resultat
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def traiter(message):
    methode = message.get("method")
    ident = message.get("id")
    params = message.get("params") or {}

    if methode == "initialize":
        repondre(ident, {
            "protocolVersion": PROTOCOLE,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "prisme", "version": VERSION},
        })
        return

    if methode in ("notifications/initialized", "initialized"):
        return                                          # notification : rien à répondre

    if methode == "tools/list":
        repondre(ident, {"tools": [{k: o[k] for k in ("name", "description", "inputSchema")}
                                   for o in OUTILS]})
        return

    if methode == "tools/call":
        nom = params.get("name")
        outil = PAR_NOM.get(nom)
        if outil is None:
            repondre(ident, erreur={"code": -32602, "message": "Outil inconnu : %s" % nom})
            return
        try:
            resultat = outil["appel"](params.get("arguments") or {})
            texte = _texte(resultat)
            erreur_outil = False
        except Souci as e:
            # Une erreur d'outil se rend DANS le résultat, pas comme erreur de protocole :
            # l'agent doit pouvoir la lire et s'adapter, pas voir sa session s'interrompre.
            texte, erreur_outil = str(e), True
        except Exception as e:                                   # noqa: BLE001
            trace("erreur inattendue sur %s : %r" % (nom, e))
            texte, erreur_outil = "Erreur inattendue de l'adaptateur : %s" % e, True
        repondre(ident, {"content": [{"type": "text", "text": texte}], "isError": erreur_outil})
        return

    if methode == "ping":
        repondre(ident, {})
        return

    repondre(ident, erreur={"code": -32601, "message": "Méthode non gérée : %s" % methode})


def main():
    if not CLE:
        trace("PRISME_CLE absente : créez une clé dans PRISME (bouton Agents) et "
              "reportez-la dans la configuration.")
    trace("adaptateur %s -> %s" % (VERSION, URL))
    for ligne in sys.stdin:
        ligne = ligne.strip()
        if not ligne:
            continue
        try:
            message = json.loads(ligne)
        except json.JSONDecodeError:
            trace("ligne illisible ignoree")
            continue
        try:
            traiter(message)
        except Exception as e:                                   # noqa: BLE001
            # L'adaptateur ne meurt jamais sur un message : le client garderait une
            # session ouverte vers un processus mort, sans aucun diagnostic.
            trace("erreur de traitement : %r" % e)
            repondre(message.get("id"), erreur={"code": -32603, "message": str(e)})


if __name__ == "__main__":
    main()
