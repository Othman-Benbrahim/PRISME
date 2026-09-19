"""Contrat E11 partagé par formulaires, agents et futurs plugins.

La complétude d'une fiche n'est pas une preuve de vérité. Aucun des cinq nouveaux
 types n'a encore de signal mécanique autorisant son entrée automatique (0021).
"""
import hashlib
import math
import re
from datetime import date

from .sources import ObjetInvalide


def champ(nom, libelle, format="texte", requis=False, choix=None):
    return dict(nom=nom, libelle=libelle, format=format, requis=requis, choix=choix or [])


TYPES = {
    "decision": dict(libelle="Décision", dossier="Decisions", champs=[
        champ("choix", "Choix retenu", requis=True),
        champ("justification", "Pourquoi ce choix", requis=True),
        champ("alternatives", "Alternatives écartées"),
        champ("decide_le", "Date de décision", "date"),
    ], statuts=["active", "remplacee", "annulee"], sections=["Contexte", "Conséquences"]),
    "hypothese": dict(libelle="Hypothèse", dossier="Hypotheses", champs=[
        champ("enonce", "Énoncé", requis=True),
        champ("critere_refutation", "Ce qui la réfuterait", requis=True),
        champ("indices", "Indices et références"),
    ], statuts=["a_examiner", "corroboree", "refutee", "abandonnee"], sections=["Arguments", "Objections"]),
    "prediction": dict(libelle="Prédiction", dossier="Predictions", champs=[
        champ("enonce", "Événement prédit", requis=True),
        champ("probabilite", "Probabilité (0 à 1)", "nombre", True),
        champ("echeance", "Date butoir", "date", True),
        champ("critere_resolution", "Condition vérifiable de résolution", requis=True),
        champ("domaine", "Domaine"),
        champ("hypothese", "Hypothèse d'origine (identifiant ou référence)"),
        champ("resultat", "Résultat", "choix", choix=["", "oui", "non", "indeterminable"]),
        champ("resolu_le", "Date de résolution", "date"),
        champ("preuve_resolution", "Preuve ou raison de la résolution"),
    ], statuts=["ouverte", "resolue", "annulee"], sections=["Raisonnement", "Sources"]),
    "entite": dict(libelle="Entité", dossier="Entites", champs=[
        champ("nature", "Nature", "choix", True,
              ["personne", "organisation", "lieu", "produit", "autre"]),
        champ("description", "Description permettant de la distinguer", requis=True),
        champ("identifiant_externe", "Identifiant externe / référence"),
        champ("alias", "Autres noms"),
    ], statuts=["active", "archivee"], sections=["Relations", "Sources"]),
    "tache": dict(libelle="Tâche", dossier="Taches", champs=[
        champ("action", "Action à réaliser", requis=True),
        champ("critere_fin", "Critère de fin", requis=True),
        champ("responsable", "Responsable"),
        champ("echeance", "Échéance", "date"),
    ], statuts=["a_faire", "en_cours", "terminee", "annulee"], sections=["Contexte", "Suivi"]),
}


def definition(type_objet):
    if not isinstance(type_objet, str) or type_objet not in TYPES:
        raise ObjetInvalide("Type d'objet inconnu")
    return TYPES[type_objet]


def texte(valeur, nom, maximum=4000):
    if not isinstance(valeur, str):
        raise ObjetInvalide("%s : texte attendu" % nom)
    valeur = valeur.strip()
    # Le sous-ensemble YAML du cœur n'accepte pas de scalaires multilignes.
    if len(valeur) > maximum or any(ord(c) < 32 for c in valeur):
        raise ObjetInvalide("%s : une ligne de %d caractères maximum" % (nom, maximum))
    return valeur


def valider(type_objet, titre, champs, *, partiel=False):
    spec = definition(type_objet)
    titre = texte(titre, "Titre", 200)
    if not titre:
        raise ObjetInvalide("Titre requis")
    if not isinstance(champs, dict):
        raise ObjetInvalide("Champs : dictionnaire attendu")
    connus = {c["nom"] for c in spec["champs"]} | {"statut"}
    if set(champs) - connus:
        raise ObjetInvalide("Champ inconnu : %s" % ", ".join(sorted(set(champs) - connus)))
    propres = {}
    for c in spec["champs"]:
        v = champs.get(c["nom"], "")
        if v is None or v == "":
            if c["requis"] and not partiel:
                raise ObjetInvalide("%s requis" % c["libelle"])
            continue
        if c["format"] == "nombre":
            if isinstance(v, bool) or not isinstance(v, (str, int, float)):
                raise ObjetInvalide("Probabilité : nombre entre 0 et 1 attendu")
            try:
                v = float(v)
            except (ValueError, OverflowError):
                raise ObjetInvalide("Probabilité : nombre entre 0 et 1 attendu") from None
            if not math.isfinite(v) or not 0 <= v <= 1:
                raise ObjetInvalide("Probabilité : nombre entre 0 et 1 attendu")
        else:
            v = texte(v, c["libelle"])
            if not v:
                if c["requis"] and not partiel:
                    raise ObjetInvalide("%s requis" % c["libelle"])
                continue
            if c["format"] == "date":
                try:
                    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                        raise ValueError()
                    date.fromisoformat(v)
                except ValueError:
                    raise ObjetInvalide("%s : date réelle AAAA-MM-JJ attendue" % c["libelle"]) from None
            if c["format"] == "choix" and v not in c["choix"]:
                raise ObjetInvalide("%s : choix invalide" % c["libelle"])
        propres[c["nom"]] = v
    statut = champs.get("statut", spec["statuts"][0])
    if statut not in spec["statuts"]:
        raise ObjetInvalide("Statut invalide")
    propres["statut"] = statut
    if type_objet == "prediction" and not partiel:
        resolution = ("resultat", "resolu_le", "preuve_resolution")
        if statut == "resolue" and not all(propres.get(k) for k in resolution):
            raise ObjetInvalide("Une résolution exige un résultat, une date et une preuve")
        if statut != "resolue" and any(propres.get(k) for k in resolution):
            raise ObjetInvalide("Les champs de résolution exigent le statut résolue")
    return titre, propres


def cle_de(type_objet, titre):
    # Une collision possible reste à relire ; elle n'écrase jamais un objet existant.
    canon = " ".join(titre.casefold().split())
    return type_objet + ":" + hashlib.sha256(canon.encode("utf-8")).hexdigest()[:24]


def gabarit(type_objet, titre, champs):
    spec = definition(type_objet)
    lignes = ["# " + titre, "", "## Fiche", ""]
    for c in spec["champs"]:
        if c["nom"] in champs:
            lignes.append("- %s : %s" % (c["libelle"], champs[c["nom"]]))
    lignes += ["", "Statut : " + champs["statut"], ""]
    for section in spec["sections"]:
        lignes += ["## " + section, "", "_À compléter._", ""]
    return "\n".join(lignes)
