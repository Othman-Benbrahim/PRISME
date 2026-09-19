"""Calculs purs du plugin : aucun score n'appartient au cœur de PRISME.

Convention binaire : Brier=(p-y)^2 ; log loss en logarithme naturel, sans écrêter
les certitudes fausses. Les groupes vides restent non calculés.
"""
import math
from collections import defaultdict
from datetime import date


def scores(p, resultat):
    if isinstance(p, bool) or not isinstance(p, (float, int)) or not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError("Probabilité finie entre 0 et 1 attendue")
    if resultat not in ('oui', 'non'):
        raise ValueError("Seuls les résultats binaires observés sont scorables")
    y = int(resultat == 'oui')
    vraisemblance = p if y else 1 - p
    perte = -math.log(vraisemblance) if vraisemblance > 0 else 'infini'
    return {'brier': (p - y) ** 2, 'log_loss': perte}


def resumer(lignes):
    n = len(lignes)
    if not n:
        return dict(n=0, brier=None, log_loss=None, probabilite_moyenne=None,
                    frequence=None, biais=None, classes=[], ece=None)
    mesures = [scores(l['probabilite'], l['resultat']) for l in lignes]
    moyenne = lambda vals: math.fsum(vals) / n
    p = moyenne([l['probabilite'] for l in lignes])
    y = moyenne([int(l['resultat'] == 'oui') for l in lignes])
    cases = defaultdict(list)
    for l in lignes:
        cases[min(9, int(l['probabilite'] * 10))].append(l)
    classes = []
    for i in range(10):
        bloc = cases[i]
        classes.append(dict(de=i / 10, a=(i + 1) / 10, n=len(bloc),
            probabilite=math.fsum(l['probabilite'] for l in bloc) / len(bloc) if bloc else None,
            frequence=sum(l['resultat'] == 'oui' for l in bloc) / len(bloc) if bloc else None))
    return dict(n=n, brier=moyenne([s['brier'] for s in mesures]),
        log_loss='infini' if any(s['log_loss'] == 'infini' for s in mesures)
                 else moyenne([s['log_loss'] for s in mesures]),
        probabilite_moyenne=p, frequence=y, biais=p-y, classes=classes,
        ece=math.fsum(c['n'] * abs(c['probabilite']-c['frequence']) for c in classes if c['n']) / n)


def groupe_horizon(jours):
    if jours <= 7: return '0–7 jours'
    if jours <= 30: return '8–30 jours'
    if jours <= 90: return '31–90 jours'
    return '91 jours et plus'


def agregats(lignes):
    domaines, horizons = defaultdict(list), defaultdict(list)
    for l in lignes:
        domaines[l.get('domaine') or 'Non renseigné'].append(l)
        horizons[groupe_horizon(l['horizon_jours'])].append(l)
    return dict(global_=resumer(lignes),
                domaines={k:resumer(v) for k,v in sorted(domaines.items())},
                horizons={k:resumer(v) for k,v in horizons.items()})


def valable_le(meta, jour):
    """True / False / None : une borne inconnue rend la réponse indéterminée.

    Intervalle fermé aux deux bouts, documenté pour que la date butoir et une
    validité dans le monde ne soient pas confondues.
    """
    d = date.fromisoformat(jour)
    inconnu = False
    for nom, debut in [('prisme_valide_du', True), ('prisme_valide_au', False)]:
        etat = meta.get(nom + '_etat', 'inconnue')
        if etat == 'ouverte':
            continue
        if etat == 'inconnue':
            inconnu = True
            continue
        if etat != 'date':
            raise ValueError('État d’horloge invalide')
        borne = date.fromisoformat(meta.get(nom, ''))
        if (debut and d < borne) or (not debut and d > borne):
            return False
    return None if inconnu else True
