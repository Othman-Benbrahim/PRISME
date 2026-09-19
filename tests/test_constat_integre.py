"""Constat local : sessions, persistance, isolation et proposition sans auto-validation."""
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from commun import ROOT, TMP, VAULT, reset_vault
from prisme_core import config, plugins
from prisme_core.api import PluginContext
from prisme_core.app import create_app
from prisme_core.objets import registre, file
from prisme_core.routes.security import TOKEN

P=ROOT/'plugins'/'constat'
spec=importlib.util.spec_from_file_location('constat_test',P/'__init__.py',submodule_search_locations=[str(P)])
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
stockage=mod.stockage

class TestConstat(unittest.TestCase):
    def setUp(self):
        reset_vault();config.wr_cfg({'workspaces':[]});file._ecrire({'entrees':[],'rejets':{}})
        self.ctx=PluginContext('constat','Constat',P,{'permissions':['vault_write','network']});mod.register(self.ctx)
        self.app=create_app(with_plugins=False);self.client=self.app.test_client()
        self.dossier=TMP/self._testMethodName;self.dossier.mkdir(exist_ok=True)
        self.ctx.data_dir=lambda:self.dossier
        self.espace=stockage.espace(self.ctx)
        self.h={'X-Prisme-Token':TOKEN,'X-Constat-Espace':self.espace}

    def appel(self,route,data=None,espace=None):
        with self.app.test_request_context(method='GET' if data is None else 'POST',json=data,
             headers={'X-Constat-Espace':espace or self.espace}):
            r=self.ctx._dispatch(route)
            if isinstance(r,tuple):return r[0].get_json(),r[1]
            return r.get_json(),200

    def donnees(self):
        return {'dossiers':['d-1'],'j:d-1':[{'t':'dossier','id':'d-1','question':'Une question'}]}

    def test_persiste_et_refuse_la_revision_perimee(self):
        _,code=self.appel('etat',{'revision':0,'donnees':self.donnees()});self.assertEqual(code,200)
        d,_=self.appel('etat');self.assertEqual(d['revision'],1);self.assertEqual(d['donnees'],self.donnees())
        _,code=self.appel('etat',{'revision':0,'donnees':{}});self.assertEqual(code,409)
        self.assertEqual(stockage.charger(self.ctx)['donnees'],self.donnees())

    def test_vaults_separes_et_panneau_perime_refuse(self):
        self.appel('etat',{'revision':0,'donnees':self.donnees()})
        autre=TMP/'constat-autre';autre.mkdir(exist_ok=True);config.wr_cfg({'workspace':str(autre)})
        self.assertEqual(stockage.charger(self.ctx)['donnees'],{})
        self.assertEqual(self.appel('etat',{'revision':0,'donnees':{}},self.espace)[1],409)

    def test_corps_verifies_et_aucun_parametre_secret_stockable(self):
        for d in [{'cle':'secret'},{'dossiers':['d-1']},{'txt:'+'0'*64:'texte'}]:
            self.assertEqual(self.appel('etat',{'revision':0,'donnees':d})[1],400)
        self.assertEqual(stockage.charger(self.ctx)['revision'],0)

    def test_source_sans_corps_ou_url_script_refusee(self):
        for source in [{'texteHash':'0'*64},{'url':'javascript:alert(1)'}]:
            d=self.donnees();d['j:d-1'].append({'t':'source',**source})
            self.assertEqual(self.appel('etat',{'revision':0,'donnees':d})[1],400)

    def test_note_copiee_sans_modifier_vault(self):
        avant=(VAULT/'Alpha.md').read_bytes()
        d,code=self.appel('note',{'chemin':'Alpha.md'});self.assertEqual(code,200);self.assertIn('Alpha',d['texte'])
        self.assertEqual((VAULT/'Alpha.md').read_bytes(),avant)

    def test_chemins_refuses(self):
        with self.assertRaises(PermissionError):self.appel('note',{'chemin':'../secret.md'})
        self.assertEqual(self.appel('note',{'chemin':[]})[1],400)

    def test_configuration_ne_transmet_pas_la_cle(self):
        with patch.object(self.ctx,'config',return_value={'api_key':'secret-test','model':'M','base_url':'https://provider.test/v1'}),patch.object(self.ctx,'ai_unavailable',return_value=None):
            d,code=self.appel('configuration');self.assertEqual(code,200);self.assertNotIn('secret-test',json.dumps(d))
            self.assertEqual(d['service'],'provider.test')

    def test_modele_explicitement_appele_une_fois(self):
        with patch.object(self.ctx,'ai_call',return_value=('{}',None)) as appel:
            d,code=self.appel('analyser',{'messages':[{'role':'user','content':'Corpus fictif'}]})
            self.assertEqual(code,200);self.assertEqual(d['texte'],'{}');appel.assert_called_once()

    def test_erreur_modele_sans_secret_ni_retry(self):
        with patch.object(self.ctx,'ai_call',return_value=(None,'clé-secret dans erreur')) as appel:
            d,code=self.appel('analyser',{'messages':[{'role':'user','content':'fictif'}]})
            self.assertEqual(code,502);self.assertNotIn('clé-secret',json.dumps(d));appel.assert_called_once()

    def test_export_estampille_et_noms_distincts(self):
        d,code=self.appel('exporter',{'contenu':'# Rapport\n\nDémonstration'});self.assertEqual(code,201)
        e,_=self.appel('exporter',{'contenu':'# Rapport'});self.assertNotEqual(d['chemin'],e['chemin'])
        meta=self.ctx.note_meta(VAULT/d['chemin']);self.assertEqual(meta['prisme_outil'],'constat')

    def test_proposition_en_file_sans_cle_agent_ni_auto_acceptation(self):
        payload={'type':'prediction','titre':'Pari Constat','champs':{'enonce':'Un événement','probabilite':.8,'echeance':'2099-01-01','critere_resolution':'Observation'},'motif':'ACH relue'}
        r=self.client.post('/api/objets/proposer',json=payload,headers=self.h)
        self.assertEqual(r.status_code,201,r.get_json());self.assertFalse(registre.lister())
        self.assertEqual(file.lister()[0]['origine'],'constat:interface')
        self.assertEqual(self.client.post('/api/objets/proposer',json=payload,headers=self.h).status_code,409)
        o=registre.accepter(r.get_json()['entree']['cle'])['objet'];self.assertTrue(o['relu']);self.assertEqual(o['champs']['probabilite'],.8)

    def test_session_et_espace_obligatoires(self):
        for h,code in [({},403),({'X-Prisme-Token':TOKEN},409)]:
            self.assertEqual(self.client.post('/api/objets/proposer',json={},headers=h).status_code,code)

    def test_ressources_modulaires_seulement_si_plugin_actif(self):
        with patch.dict(plugins.REGISTRY,{},clear=True):
            p=plugins.load_one(P)
            for route in ['web/index.html','web/app.js','web/core/etapes.js','web/references/ach-heuer.md']:
                with self.client.get('/plugins/constat/'+route) as r:self.assertEqual(r.status_code,200)
            for route in ['__init__.py','web/../__init__.py','web/.env','web/package.json']:
                with self.client.get('/plugins/constat/'+route) as r:self.assertEqual(r.status_code,404)
            plugins.deactivate('constat')
            self.assertEqual(self.client.get('/plugins/constat/web/index.html').status_code,404)

    def test_pas_de_monolithe_ni_api_firefox(self):
        for f in (P/'web').rglob('*'):
            if f.suffix in ('.js','.css','.html'):
                texte=f.read_text(encoding='utf-8');self.assertLess(len(texte),20000,f.name)
                self.assertNotIn('browser.runtime.',texte);self.assertNotIn('browser.storage.local.get(',texte)
