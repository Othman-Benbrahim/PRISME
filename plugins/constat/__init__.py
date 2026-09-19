"""Constat intégré : le navigateur calcule, PRISME persiste et appelle son modèle."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit
from flask import jsonify, request
from . import stockage


def register(ctx):
    def json_objet():
        d=request.get_json(silent=True)
        if not isinstance(d,dict):
            raise ValueError('Objet JSON attendu')
        return d

    def borner():
        if request.headers.get('X-Constat-Espace') != stockage.espace(ctx):
            raise stockage.Conflit('Le vault a changé. Rechargez Constat avant de continuer.')

    def note(chemin):
        if not isinstance(chemin,str):
            raise ValueError('Chemin attendu')
        p=ctx.safe_path(chemin, must_exist=True)
        if ctx.vault_root() not in p.parents or p.suffix.lower() != '.md' or '.trash' in p.relative_to(ctx.vault_root()).parts:
            raise PermissionError('Choisissez une note du vault principal')
        return p

    def proteger(fn):
        def appel(*args,**kw):
            try:
                borner()
                return fn(*args,**kw)
            except stockage.Conflit as e:
                return jsonify(error=str(e)),409
            except (ValueError, TypeError) as e:
                return jsonify(error=str(e)),400
        appel.__name__=fn.__name__
        return appel

    @ctx.route('/etat')
    def etat():
        return jsonify(stockage.charger(ctx))

    @ctx.route('/etat',methods=['POST'])
    @proteger
    def sauver():
        d=json_objet()
        return jsonify(revision=stockage.enregistrer(ctx,d.get('revision'),d.get('donnees')))

    @ctx.route('/configuration')
    @proteger
    def configuration():
        c=ctx.config()
        return jsonify(modele=c.get('model',''), service=urlsplit(c.get('base_url','')).hostname or 'local',
                       indisponible=ctx.ai_unavailable())

    @ctx.route('/notes')
    @proteger
    def notes():
        out=[]
        for p in ctx.iter_notes():
            try:
                p=note(str(p));out.append(dict(chemin=p.relative_to(ctx.vault_root()).as_posix(),titre=p.stem))
            except (OSError,ValueError):
                continue
        return jsonify(notes=out)

    @ctx.route('/note',methods=['POST'])
    @proteger
    def lire():
        p=note(json_objet().get('chemin'))
        if p.stat().st_size > 2*1024*1024:
            raise ValueError('Note trop volumineuse (2 Mio maximum)')
        return jsonify(texte=ctx.read_note(p),titre=p.stem,chemin=p.relative_to(ctx.vault_root()).as_posix())

    @ctx.route('/analyser',methods=['POST'])
    @proteger
    def analyser():
        d=json_objet();messages=d.get('messages')
        if not isinstance(messages,list) or not 1 <= len(messages) <= 4:
            raise ValueError('Messages d’analyse attendus')
        if any(not isinstance(m,dict) or m.get('role') not in ('system','user') or not isinstance(m.get('content'),str) for m in messages):
            raise ValueError('Messages invalides')
        if sum(len(m['content']) for m in messages)>180_000:
            raise ValueError('Corpus trop volumineux pour un appel : réduisez-le explicitement')
        c=ctx.config()
        texte,erreur=ctx.ai_call(messages,max_tokens=8000,temperature=.2,timeout=120)
        # Les détails réseau peuvent contenir des secrets du fournisseur.
        if erreur:
            return jsonify(error='L’analyse a échoué. Vérifiez le modèle dans les paramètres PRISME ; aucun renvoi automatique.'),502
        borner()
        return jsonify(texte=texte,modele=c.get('model',''),service=urlsplit(c.get('base_url','')).hostname or 'local',
                       produit_le=datetime.now(timezone.utc).isoformat())

    @ctx.route('/exporter',methods=['POST'])
    @proteger
    def exporter():
        d=json_objet();contenu=d.get('contenu')
        if not isinstance(contenu,str) or not contenu.strip() or len(contenu)>2_000_000:
            raise ValueError('Rapport Markdown attendu (2 millions de caractères maximum)')
        p=ctx.safe_path('Rapports/Constat-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+uuid4().hex[:8]+'.md')
        if ctx.vault_root() not in p.parents or p.exists():
            raise PermissionError('Destination indisponible')
        ctx.write_note(p,contenu,provenance={'type':'rapport_constat','genere_par':'assemblage local Constat ; analyses attribuées dans le rapport'})
        return jsonify(chemin=p.relative_to(ctx.vault_root()).as_posix()),201
