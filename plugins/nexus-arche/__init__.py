"""NEXUS-ARCHÊ — catalogue, valideur de signature, tirage et lecture assistée.

Seule `/lire` appelle un modèle. Tout le reste — catalogue, distinctions, signature,
tirage — répond hors ligne. Et ce que le modèle rend passe par les garde-fous de
`lecture.py` avant d'atteindre l'auteur.
"""
import json

from flask import Response, jsonify, request

from . import catalogue, configurations, fiche, lecture, sigma, tirage


def _json(charge, code=200):
    """Réponse JSON en UTF-8 réel, sans échappement.

    `jsonify` échappe le non-ASCII : chaque glyphe devient `\\u22a5`, six caractères
    au lieu d'un. Sur ce plugin, dont tout le contenu est accentué et glyphique, cela
    gonfle le catalogue de plus de moitié — et rendrait illisible toute charge destinée
    plus tard à un modèle.
    """
    return Response(json.dumps(charge, ensure_ascii=False),
                    status=code, mimetype="application/json; charset=utf-8")


def register(ctx):
    @ctx.route('/catalogue')
    def voir_catalogue():
        cartes = catalogue.toutes()
        return _json({'cartes': cartes, 'total': len(cartes)})

    @ctx.route('/distinctions')
    def voir_distinctions():
        a, b = (request.args.get('a') or '').strip(), (request.args.get('b') or '').strip()
        if not catalogue.existe(a) or not catalogue.existe(b):
            return jsonify(error='Carte inconnue : %s' % (a if not catalogue.existe(a) else b)), 400
        return _json({'questions': catalogue.questions_entre(a, b)})

    @ctx.route('/valider_signature', methods=['POST'])
    def valider_signature():
        d = request.get_json(silent=True)
        if not isinstance(d, dict):
            return jsonify(error='Objet JSON attendu'), 400
        return _json(sigma.valider(d.get('chaine', ''),
                                   exiger_statut=d.get('exiger_statut', True)))

    @ctx.route('/etat')
    def etat():
        """Ce que l'interface doit savoir avant d'offrir la lecture assistée."""
        return _json({'ia_indisponible': ctx.ai_unavailable(),
                      'modes': {str(k): v['nom'] for k, v in tirage.MODES.items()},
                      'max_cartes': lecture.MAX_CARTES,
                      'formats': fiche.FORMATS, 'statuts': fiche.STATUTS,
                      'dossier_fiches': fiche.DOSSIER})

    @ctx.route('/tirage', methods=['POST'])
    def faire_tirage():
        d = request.get_json(silent=True)
        if not isinstance(d, dict):
            return jsonify(error='Objet JSON attendu'), 400
        try:
            return _json(tirage.tirer(int(d.get('mode') or 0)))
        except (TypeError, ValueError) as e:
            return jsonify(error=str(e)), 400

    @ctx.route('/lire', methods=['POST'])
    def lire():
        d = request.get_json(silent=True)
        if not isinstance(d, dict):
            return jsonify(error='Objet JSON attendu'), 400
        imposees = d.get('imposees') or None
        if imposees is not None:
            if not isinstance(imposees, list) or not all(catalogue.existe(str(i)) for i in imposees):
                return jsonify(error='Cartes imposées inconnues du catalogue'), 400
            imposees = [str(i) for i in imposees]
        resultat, erreur = lecture.proposer(ctx, d.get('situation', ''), imposees)
        if erreur:
            return jsonify(error=erreur), 400
        resultat['distinctions'] = lecture.questions_de_distinction(resultat['retenues'])

        # Les positions viennent du tirage ; une carte écartée n'en occupe aucune.
        positions = d.get('positions') or {}
        if isinstance(positions, dict):
            for c in resultat['retenues']:
                c['position'] = str(positions.get(c['id']) or '')
            actives, inactives = configurations.positions_actives(
                resultat['retenues'],
                [{'id': i, 'position': p} for i, p in positions.items()])
            resultat['configurations'] = configurations.detecter(actives)
            resultat['positions_inactives'] = inactives
        return _json(resultat)

    @ctx.route('/fiche', methods=['POST'])
    def ecrire_fiche():
        """Archive la lecture dans le vault. L'auteur choisit le format ; le code
        revérifie les ancrages et recalcule les configurations avant d'écrire."""
        d = request.get_json(silent=True)
        if not isinstance(d, dict):
            return jsonify(error='Objet JSON attendu'), 400
        propres, erreur = fiche.consolider(d)
        if erreur:
            return jsonify(error=erreur), 400
        try:
            texte = fiche.markdown(propres, d.get('format') or 'longue')
        except ValueError as e:
            return jsonify(error=str(e)), 400
        chemin = ctx.safe_path(fiche.nom_fichier())
        try:
            ecrit = ctx.write_note(chemin, texte,
                                   provenance={'type': 'lecture_nexus'}, exclusive=True)
        except (FileExistsError, PermissionError) as e:
            return jsonify(error=str(e)), 400
        return _json({'chemin': ecrit.relative_to(ctx.vault_root()).as_posix(),
                      'format': d.get('format') or 'longue',
                      'configurations': propres['configurations']}, 201)
