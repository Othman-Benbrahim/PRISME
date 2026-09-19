"""Données Constat par vault, révision optimiste et transaction SQLite unique."""
import hashlib
import json
import re
import sqlite3
from urllib.parse import urlsplit
from contextlib import contextmanager

MAX_TAILLE = 20 * 1024 * 1024


def espace(ctx):
    return hashlib.sha256(str(ctx.vault_root()).encode('utf-8')).hexdigest()


@contextmanager
def connexion(ctx):
    p = ctx.data_dir() / ('dossiers-' + espace(ctx) + '.sqlite3')
    c = sqlite3.connect(p, timeout=10)
    try:
        c.execute('CREATE TABLE IF NOT EXISTS etat (id INTEGER PRIMARY KEY, revision INTEGER NOT NULL, donnees TEXT NOT NULL)')
        c.execute("INSERT OR IGNORE INTO etat VALUES (1, 0, '{}')")
        c.commit()
        yield c
    finally:
        c.close()


def charger(ctx):
    with connexion(ctx) as c:
        rev, texte = c.execute('SELECT revision, donnees FROM etat WHERE id=1').fetchone()
    return dict(espace=espace(ctx), revision=rev, donnees=json.loads(texte))


def valider(d):
    if not isinstance(d, dict):
        raise ValueError('Données Constat attendues')
    for k, v in d.items():
        if k == 'dossiers':
            if not isinstance(v, list) or len(v) > 1000 or len(set(v)) != len(v):
                raise ValueError('Index des dossiers invalide')
            if any(not isinstance(i,str) or not re.fullmatch(r'[\w-]{1,100}', i) for i in v):
                raise ValueError('Identifiant de dossier invalide')
        elif re.fullmatch(r'j:[\w-]{1,100}',k):
            if not isinstance(v,list) or any(not isinstance(e,dict) or not isinstance(e.get('t'),str) for e in v):
                raise ValueError('Journal de dossier invalide')
        elif re.fullmatch(r'txt:[a-f0-9]{64}',k):
            if not isinstance(v,str) or hashlib.sha256(v.encode('utf-8')).hexdigest() != k[4:]:
                raise ValueError('Empreinte du texte incorrecte')
        else:
            raise ValueError('Clé de stockage non autorisée')
    for ident in d.get('dossiers',[]):
        j=d.get('j:'+ident)
        if not j or not any(e.get('t')=='dossier' and e.get('id')==ident for e in j):
            raise ValueError('Dossier sans journal')
        for e in j:
            if e.get('t')=='source':
                for nom in ('url','canonical'):
                    if not e.get(nom): continue
                    u=urlsplit(e[nom])
                    if u.scheme not in ('http','https') or not u.hostname or u.username or u.password:
                        raise ValueError('URL de source non autorisée')
            if e.get('t')=='source' and e.get('texteHash') and 'txt:'+e['texteHash'] not in d:
                raise ValueError('Corps de source manquant')
    texte = json.dumps(d, ensure_ascii=False, allow_nan=False)
    if len(texte.encode('utf-8')) > MAX_TAILLE:
        raise ValueError('Limite de 20 Mio par vault atteinte : exportez les dossiers')
    return texte


def enregistrer(ctx, revision, donnees):
    if isinstance(revision,bool) or not isinstance(revision,int):
        raise ValueError('Révision attendue')
    texte=valider(donnees)
    with connexion(ctx) as c:
        c.execute('BEGIN IMMEDIATE')
        n=c.execute('UPDATE etat SET revision=revision+1, donnees=? WHERE id=1 AND revision=?',(texte,revision)).rowcount
        if n != 1:
            c.rollback()
            raise Conflit('Un autre panneau a modifié les dossiers. Rechargez avant de reprendre.')
        c.commit()
    return revision+1


class Conflit(ValueError):
    pass
