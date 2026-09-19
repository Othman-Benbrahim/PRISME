"""Copies de référence dans le vault ; aucune confiance dans une note modifiée.

La copie et son empreinte détectent les modifications accidentelles. Elles ne
résistent pas à une personne qui réécrit les deux : ce n'est pas un tiers d'horodatage.
"""
import base64
import hashlib
import json
import re
import threading
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from prisme_core.api import update_frontmatter
from .calculs import agregats, scores, valable_le

VERROU = threading.Lock()
DOSSIER = 'Objets/Calibration'
FIGES = ('enonce', 'probabilite', 'echeance', 'critere_resolution', 'domaine', 'hypothese')


def maintenant():
    return datetime.now(timezone.utc)


def canon(d):
    return json.dumps(d, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def empreinte(d):
    return hashlib.sha256(canon(d).encode('utf-8')).hexdigest()


def principal(ctx, chemin):
    if not isinstance(chemin, (str, Path)):
        raise ValueError("Chemin de note attendu")
    p = ctx.safe_path(chemin)
    if p != ctx.vault_root() and ctx.vault_root() not in p.parents:
        raise PermissionError('La calibration appartient au vault principal')
    return p


def objet(ctx, chemin):
    p = principal(ctx, chemin)
    o = ctx.typed_object(p)
    m = ctx.note_meta(p)
    if o['type'] != 'prediction' or not o['id'] or not o['relu'] or m.get('prisme_schema') != '1':
        raise ValueError('Prédiction E11 relue avec identifiant stable requise')
    return o, m


def noyau(o):
    return {k:o['champs'].get(k, '') for k in FIGES}


def lire_pieces(ctx, meta):
    """Instantané lisible du rapport d'origine ; pas de dépendance à Constat."""
    origine = str(meta.get('prisme_origine', ''))
    chemin = meta.get('prisme_note_origine', '')
    if not origine.startswith('constat:') or not chemin:
        return None  # Les anciennes prédictions restent utilisables, sans inventer leurs pièces.
    p = principal(ctx, chemin)
    if p.suffix.lower() != '.md' or not p.is_file():
        raise ValueError('Pièces Constat absentes : restaurez la note avant de copier le pari')
    if p.stat().st_size > 210_000:
        raise ValueError('Pièces trop volumineuses (210 ko avec provenance)')
    texte = ctx.read_note(p)
    return dict(chemin=p.relative_to(ctx.vault_root()).as_posix(), texte=texte,
                sha256=hashlib.sha256(texte.encode('utf-8')).hexdigest())


def lire_copie(ctx, p):
    meta = ctx.note_meta(principal(ctx, p))
    if meta.get('prisme_type') != 'calibration_archive':
        raise ValueError('Copie de référence invalide')
    brut = meta.get('prisme_calibration_donnees', '')
    if not isinstance(brut, str) or len(brut) > 400_000:
        raise ValueError('Copie trop volumineuse ou invalide')
    try:
        d = json.loads(base64.b64decode(brut, validate=True).decode('utf-8'))
    except (ValueError, UnicodeError):
        raise ValueError('Copie illisible') from None
    if not isinstance(d, dict) or d.get('version') != 1 or empreinte(d) != meta.get('prisme_calibration_sha256'):
        raise ValueError('Empreinte de la copie modifiée')
    if not isinstance(d.get('id'), str) or not re.fullmatch(r'[a-f0-9]{12}', d['id']):
        raise ValueError('Identifiant de copie invalide')
    if not isinstance(d.get('pari'), dict) or set(d['pari']) != set(FIGES):
        raise ValueError('Pari archivé incomplet')
    pieces = d.get('pieces_constat')
    if pieces is not None and (not isinstance(pieces, dict) or not isinstance(pieces.get('texte'), str)
            or hashlib.sha256(pieces['texte'].encode('utf-8')).hexdigest() != pieces.get('sha256')):
        raise ValueError('Empreinte des pièces modifiée')
    scores(d['pari']['probabilite'], 'oui')
    horodatage = datetime.fromisoformat(d['capture_le'])
    if not horodatage.tzinfo or horodatage > maintenant():
        raise ValueError('Date de copie invalide')
    if date.fromisoformat(d['pari']['echeance']) <= horodatage.date():
        raise ValueError('Copie postérieure à la date butoir')
    return d


def inscrire(ctx, chemin, horloge, version, version_pieces=None):
    with VERROU:
        o, meta = objet(ctx, chemin)
        ident = o['id']
        if not re.fullmatch(r'[a-f0-9]{12}', ident):
            raise ValueError('Identifiant E11 invalide')
        p = principal(ctx, o['chemin'])
        if hashlib.sha256(ctx.read_note(p).encode('utf-8')).hexdigest() != version:
            raise ValueError('La note a changé : actualisez avant de confirmer')
        if o['champs']['statut'] != 'ouverte':
            raise ValueError('Seule une prédiction encore ouverte peut être inscrite')
        instant = maintenant()
        if date.fromisoformat(o['champs']['echeance']) <= instant.date():
            raise ValueError('La date butoir doit être après aujourd’hui (UTC)')
        copies = principal(ctx, f'{DOSSIER}/{ident}.md')
        if copies.exists():
            raise ValueError('Ce pari possède déjà sa copie de référence ; elle ne sera pas remplacée')
        # Évite de réutiliser un identifiant dupliqué dans une note copiée à la main.
        memes = [n for n in ctx.iter_notes() if ctx.note_meta(principal(ctx, n)).get('prisme_id') == ident]
        if len(memes) != 1:
            raise ValueError('Identifiant dupliqué dans le vault')
        pieces = lire_pieces(ctx, meta)
        if pieces and pieces['sha256'] != version_pieces:
            raise ValueError('Les pièces ont changé ou n’ont pas été relues : actualisez avant de confirmer')
        ctx.set_world_clock(p, horloge)
        m = ctx.note_meta(p)
        d = dict(version=1, id=ident, titre=o['titre'], chemin=o['chemin'], pari=noyau(o),
                 capture_le=instant.isoformat(), enregistre_le=o['enregistre_le'],
                 horloge={k:m.get(k, '') for k in horloge})
        if pieces:
            d['pieces_constat'] = pieces
        payload = base64.b64encode(canon(d).encode('utf-8')).decode('ascii')
        if len(payload) > 400_000:
            raise ValueError('Copie trop volumineuse : réduisez les pièces explicitement')
        corps = '# Copie de référence — ' + o['titre'] + '\n\n'
        corps += 'Copie locale datée ; pas un horodatage certifié. Ne pas modifier.\n\n'
        corps += '```json\n' + json.dumps(d, ensure_ascii=False, indent=2) + '\n```\n'
        contenu = update_frontmatter(corps, {'prisme_calibration_donnees': payload,
                        'prisme_calibration_sha256': empreinte(d), 'prisme_calibration_prediction':ident})
        ctx.write_note(copies, contenu, provenance={'type':'calibration_archive', 'genere_par':'calcul déterministe local (sans modèle)'}, exclusive=True)
        return dict(id=ident, copie=copies.relative_to(ctx.vault_root()).as_posix(), capture_le=d['capture_le'])


def inventaire(ctx):
    objets, problemes = [], []
    for p in ctx.iter_notes():
        try:
            p = principal(ctx, p)
            m = ctx.note_meta(p)
            if m.get('prisme_type') != 'prediction':
                continue
            o, m = objet(ctx, p)
            o['horloge'] = {k:m.get(k, '') for k in ('prisme_valide_du','prisme_valide_au',
                             'prisme_valide_du_etat','prisme_valide_au_etat')}
            o['version'] = hashlib.sha256(ctx.read_note(p).encode('utf-8')).hexdigest()
            o['inscrite'] = principal(ctx, f"{DOSSIER}/{o['id']}.md").exists()
            o['pieces'] = lire_copie(ctx, principal(ctx, f"{DOSSIER}/{o['id']}.md")).get('pieces_constat') if o['inscrite'] else lire_pieces(ctx, m)
            objets.append(o)
        except (OSError, ValueError) as e:
            problemes.append({'chemin':str(p), 'raison':str(e)})
    return objets, problemes


def rapport(ctx, jour=None):
    if jour:
        if not isinstance(jour, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', jour):
            raise ValueError('Date de filtre attendue : AAAA-MM-JJ')
        date.fromisoformat(jour)
    objets, erreurs = inventaire(ctx)
    exclus = [{'raison':'fiche_invalide', **e} for e in erreurs]
    comptes = Counter(o['id'] for o in objets)
    par_id = {o['id']:o for o in objets}
    lignes, vus = [], set()
    racine = principal(ctx, DOSSIER)
    copies = list(ctx.iter_notes(racine)) if racine.exists() else []
    valides = []
    for p in copies:
        try:
            valides.append((p, lire_copie(ctx, p)))
        except (OSError, ValueError, KeyError, TypeError) as e:
            exclus.append(dict(chemin=p.relative_to(ctx.vault_root()).as_posix(), raison=str(e)))
    comptes_copies = Counter(d['id'] for _, d in valides)
    for p, d in valides:
        ident = d['id']
        vus.add(ident)
        try:
            if comptes_copies[ident] != 1:
                raise ValueError('Copie dupliquée : aucune version ne sera choisie arbitrairement')
            if comptes[ident] != 1:
                raise ValueError('Prédiction absente ou identifiant dupliqué')
            o = par_id[ident]
            if noyau(o) != d['pari']:
                raise ValueError('Pari modifié depuis la copie ; créer un nouvel objet pour un nouveau pari')
            if o['champs']['statut'] != 'resolue':
                raise ValueError('Prédiction ' + o['champs']['statut'])
            if o['champs'].get('resultat') not in ('oui', 'non'):
                raise ValueError('Résultat indéterminable : exclu du scoring')
            capture = datetime.fromisoformat(d['capture_le']).date()
            resolution = date.fromisoformat(o['champs']['resolu_le'])
            if not capture <= resolution <= maintenant().date():
                raise ValueError('Date de résolution antérieure à la copie ou future')
            if jour:
                valable = valable_le(d['horloge'], jour)
                if valable is not True:
                    raise ValueError('Validité inconnue à cette date' if valable is None else 'Hors de la période du monde')
            ligne = dict(id=ident, titre=o['titre'], chemin=o['chemin'],
                probabilite=d['pari']['probabilite'], resultat=o['champs']['resultat'],
                domaine=d['pari']['domaine'], echeance=d['pari']['echeance'],
                horizon_jours=(date.fromisoformat(d['pari']['echeance'])-capture).days,
                capture_le=d['capture_le'], resolu_le=o['champs']['resolu_le'],
                preuve_resolution=o['champs']['preuve_resolution'], copie=str(p.relative_to(ctx.vault_root()).as_posix()))
            lignes.append({**ligne, **scores(ligne['probabilite'], ligne['resultat'])})
        except (OSError, ValueError, KeyError, TypeError) as e:
            exclus.append(dict(id=ident, chemin=str(p.relative_to(ctx.vault_root()).as_posix()), raison=str(e)))
    for o in objets:
        if o['id'] not in vus:
            exclus.append(dict(id=o['id'], chemin=o['chemin'], raison='Sans copie de référence avant échéance'))
    return dict(version=1, calcule_le=maintenant().isoformat(), filtre_monde=jour,
                lignes=lignes, exclus=exclus, **agregats(lignes))


def markdown(r):
    def propre(v):
        return str(v).replace('|','\\|').replace('\n',' ')
    def nombre(v):
        return 'non calculé' if v is None else ('∞' if v == 'infini' else f'{v:.6g}')
    g=r['global_']
    lignes=['# Calibration des prédictions', '', 'Calculé le : '+r['calcule_le'], '',
        f"{g['n']} prédiction(s) scorée(s) ; {len(r['exclus'])} exclusion(s).", '',
        'Brier : '+nombre(g['brier'])+' · Log loss : '+nombre(g['log_loss']), '',
        'Biais moyen p − résultat : '+nombre(g['biais'])+' · ECE (10 classes) : '+nombre(g['ece']), '',
        'Statistiques descriptives : un petit effectif ne prouve pas un biais systématique.',
        'Copies locales modifiables, sans tiers d’horodatage. Le filtre monde décrit la validité, pas la connaissance passée.', '']
    for titre, groupes in [('Par domaine',r['domaines']),('Par horizon à la copie',r['horizons'])]:
        lignes += ['## '+titre,'','| Groupe | n | Brier | Log loss | Biais |','|---|---:|---:|---:|---:|']
        for nom,s in groupes.items():
            lignes.append(f"| {propre(nom)} | {s['n']} | {nombre(s['brier'])} | {nombre(s['log_loss'])} | {nombre(s['biais'])} |")
        lignes.append('')
    lignes += ['## Classes de calibration', '', '| Intervalle | n | p moyen | Fréquence observée |', '|---|---:|---:|---:|']
    for i,c in enumerate(g['classes']):
        lignes.append(f"| [{c['de']} ; {c['a']}{']' if i == 9 else '['} | {c['n']} | {nombre(c['probabilite'])} | {nombre(c['frequence'])} |")
    lignes += ['', 'Filtre de validité dans le monde : '+(r['filtre_monde'] or 'aucun'), '']
    lignes += ['## Paris scorés', '', '| Prédiction | p | Résultat | Brier | Log loss | Copie |', '|---|---:|---|---:|---:|---|']
    for l in r['lignes']:
        lignes.append(f"| {propre(l['titre'])} | {l['probabilite']} | {l['resultat']} | {nombre(l['brier'])} | {nombre(l['log_loss'])} | {propre(l['copie'])} |")
    lignes += ['', '## Résolutions observées', '', '| Prédiction | Résolue le | Preuve |', '|---|---|---|']
    for l in r['lignes']:
        lignes.append(f"| {propre(l['titre'])} | {l['resolu_le']} | {propre(l['preuve_resolution'])} |")
    lignes += ['', '## Exclusions', '']
    lignes += ['- '+propre(e['chemin'])+' : '+propre(e['raison']) for e in r['exclus']]
    return '\n'.join(lignes)+'\n'
