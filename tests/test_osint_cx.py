"""La recherche multi-source et son score fonctionnent avec les connecteurs actuels."""
import importlib.util
import json
import unittest
from unittest.mock import patch
from commun import ROOT
from flask import Flask
from prisme_core.api import PluginContext

DOSSIER=ROOT/'plugins'/'osint-cx'
spec=importlib.util.spec_from_file_location('osint_cx_test',DOSSIER/'__init__.py')
plugin=importlib.util.module_from_spec(spec);spec.loader.exec_module(plugin)


class TestOsintCx(unittest.TestCase):
    def test_sources_restantes_et_correlation(self):
        app=Flask(__name__)
        with app.test_request_context('/?github=1&x=1'), \
             patch.object(plugin,'search_username',return_value={'ok':True,'results':[]}), \
             patch.object(plugin,'search_github_profile',return_value={'ok':True,'found':True,'profile':{'name':'Alice','login':'alice'}}), \
             patch.object(plugin,'search_x_profile',return_value={'ok':True,'found':True,'profile':{'name':'Alice','username':'alice'}}):
            d=plugin.crossref('alice','username')
        self.assertEqual(set(d),{'ok','query','type','results','github','x_profile','correlation'})
        self.assertTrue(d['ok'])
        self.assertGreater(d['correlation']['score'],0)

    def test_secrets_et_routes_conserves(self):
        manifest=json.loads((DOSSIER/'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual({s['name'] for s in manifest['secrets']},{'X_BEARER_TOKEN','RAPIDAPI_KEY'})
        ctx=PluginContext('osint-cx','OSINT',DOSSIER,manifest);routes=[]
        def route(path,**kw):
            routes.append(path)
            return lambda fn:fn
        ctx.route=route;plugin.register(ctx)
        self.assertEqual(set(routes),{'/ping','/username','/email','/phone','/ip','/domain','/crossref',
                                     '/github','/wikidata','/entreprise','/reddit','/x','/linkedin','/social-cli','/score'})
