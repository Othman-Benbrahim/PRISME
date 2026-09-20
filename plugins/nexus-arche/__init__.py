"""NEXUS-ARCHÊ — lot 1 : catalogue et valideur de signature.

Rien ici n'appelle de modèle ni le réseau. Les deux routes sont déterministes et
répondent hors ligne.
"""
import json

from flask import Response, jsonify, request

from . import catalogue, sigma


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
