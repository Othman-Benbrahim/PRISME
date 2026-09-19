"""Calibration facultative : calcul, rapport et copies dans le plugin (0025)."""
from flask import jsonify, request
from . import registre


def register(ctx):
    @ctx.route('/predictions')
    def predictions():
        objets, erreurs = registre.inventaire(ctx)
        return jsonify(objets=objets, erreurs=erreurs)

    @ctx.route('/inscrire', methods=['POST'])
    def inscrire():
        d=request.get_json(silent=True)
        if not isinstance(d, dict):
            return jsonify(error='Objet JSON attendu'), 400
        try:
            return jsonify(registre.inscrire(ctx, d.get('chemin',''), d.get('horloge',{}), d.get('version'), d.get('version_pieces'))), 201
        except (ValueError, FileExistsError) as e:
            return jsonify(error=str(e)), 400

    @ctx.route('/rapport')
    def rapport():
        try:
            return jsonify(registre.rapport(ctx, request.args.get('jour') or None))
        except ValueError as e:
            return jsonify(error=str(e)), 400

    @ctx.route('/exporter', methods=['POST'])
    def exporter():
        d=request.get_json(silent=True)
        if not isinstance(d, dict):
            return jsonify(error='Objet JSON attendu'), 400
        try:
            r=registre.rapport(ctx, d.get('jour') or None)
            nom='Calibration-'+registre.maintenant().strftime('%Y%m%d-%H%M%S-%f')+'.md'
            p=registre.principal(ctx, 'Rapports/'+nom)
            ctx.write_note(p, registre.markdown(r), provenance={'type':'rapport_calibration', 'genere_par':'calcul déterministe local (sans modèle)'}, exclusive=True)
            return jsonify(chemin=p.relative_to(ctx.vault_root()).as_posix()), 201
        except ValueError as e:
            return jsonify(error=str(e)), 400
