"""Horloge du monde : états explicites et bornes réelles, sans calcul de score.

L'API du plugin de calibration l'active sur un geste de l'auteur (0026).
Une borne inconnue ne devient jamais une borne ouverte par défaut.
"""
import re
from datetime import date

CHAMPS = ('prisme_valide_du', 'prisme_valide_au',
          'prisme_valide_du_etat', 'prisme_valide_au_etat')


def valider(champs):
    if not isinstance(champs, dict) or set(champs) != set(CHAMPS):
        raise ValueError("Fournir les deux bornes et leurs états")
    propres = {}
    for nom in ('prisme_valide_du', 'prisme_valide_au'):
        etat = champs[nom + '_etat']
        valeur = champs[nom]
        if etat not in ('date', 'inconnue', 'ouverte'):
            raise ValueError("État attendu : date, inconnue ou ouverte")
        if etat == 'date':
            if not isinstance(valeur, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', valeur):
                raise ValueError("Date attendue : AAAA-MM-JJ")
            date.fromisoformat(valeur)
            propres[nom] = valeur
        else:
            if valeur not in ('', None):
                raise ValueError("Une borne inconnue ou ouverte ne porte pas de date")
            propres[nom] = None
        propres[nom + '_etat'] = etat
    if propres['prisme_valide_du'] and propres['prisme_valide_au']:
        if propres['prisme_valide_du'] > propres['prisme_valide_au']:
            raise ValueError("La fin de validité précède son début")
    return propres
