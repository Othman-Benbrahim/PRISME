"""Scores connus et refus qui empêchent de réécrire un pari après coup."""
import importlib.util
import json
import math
import shutil
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from commun import ROOT, TMP, VAULT, reset_vault
from prisme_core import config, frontmatter, horloge
from prisme_core.api import PluginContext, PluginPermissionError
from prisme_core.app import create_app
from prisme_core.objets import registre as objets

# Chargement isolé : ne dépend ni des plugins activés ni du registre d'autres tests.
DOSSIER = ROOT / 'plugins' / 'calibration'
spec = importlib.util.spec_from_file_location('calibration_test', DOSSIER / '__init__.py', submodule_search_locations=[str(DOSSIER)])
plugin = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugin
spec.loader.exec_module(plugin)
registre = sys.modules['calibration_test.registre']
calculs = sys.modules['calibration_test.calculs']
INCONNUE = dict(prisme_valide_du=None, prisme_valide_au=None, prisme_valide_du_etat='inconnue', prisme_valide_au_etat='inconnue')
OUVERTE = dict(INCONNUE, prisme_valide_du_etat='ouverte', prisme_valide_au_etat='ouverte')


class TestCalculs(unittest.TestCase):
    def test_mesure_rejouable(self):
        lignes = [dict(probabilite=.8, resultat='oui', domaine='A', horizon_jours=7),
                  dict(probabilite=.6, resultat='non', domaine='A', horizon_jours=8)]
        r = calculs.agregats(lignes)
        self.assertAlmostEqual(r['global_']['brier'], .2)
        self.assertAlmostEqual(r['global_']['log_loss'], -.5 * math.log(.32))
        self.assertAlmostEqual(r['global_']['biais'], .2)
        self.assertAlmostEqual(r['global_']['ece'], .4)
        self.assertEqual(r['domaines']['A']['n'], 2)
        self.assertEqual([s['n'] for s in r['horizons'].values()], [1,1])

    def test_certitudes_sans_ecretage_et_json_strict(self):
        self.assertEqual(calculs.scores(0,'non')['log_loss'], 0)
        self.assertEqual(calculs.scores(1,'oui')['brier'], 0)
        self.assertEqual(calculs.scores(1,'non')['log_loss'], 'infini')
        s=calculs.resumer([dict(probabilite=1, resultat='non')])
        self.assertEqual(s['classes'][-1]['n'], 1)
        json.dumps(s, allow_nan=False)

    def test_invalides_et_vide(self):
        for p in (True, False, '0.5', None, -1, 2, float('nan'), float('inf')):
            with self.subTest(p=p), self.assertRaises(ValueError): calculs.scores(p,'oui')
        with self.assertRaises(ValueError): calculs.scores(.5,'indeterminable')
        self.assertIsNone(calculs.resumer([])['brier'])
        self.assertEqual([calculs.groupe_horizon(n) for n in (7,8,30,31,90,91)],
                         ['0–7 jours','8–30 jours','8–30 jours','31–90 jours','31–90 jours','91 jours et plus'])

    def test_horloge_trois_etats_et_bornes_incluses(self):
        self.assertIsNone(calculs.valable_le(INCONNUE,'2030-01-01'))
        self.assertTrue(calculs.valable_le(OUVERTE,'2030-01-01'))
        h=dict(OUVERTE, prisme_valide_du='2030-01-01', prisme_valide_du_etat='date')
        self.assertTrue(calculs.valable_le(h,'2030-01-01'))
        self.assertFalse(calculs.valable_le(h,'2029-12-31'))
        for mod in ({'prisme_valide_du':'2030-01-01'}, {'prisme_valide_du_etat':'date'},
                    {'prisme_valide_du':'2030-02-30','prisme_valide_du_etat':'date'},
                    {'prisme_valide_du':'2030-02-02','prisme_valide_du_etat':'date',
                     'prisme_valide_au':'2030-01-01','prisme_valide_au_etat':'date'}):
            with self.assertRaises(ValueError): horloge.valider(dict(INCONNUE, **mod))


class TestCopiesEtRapports(unittest.TestCase):
    def setUp(self):
        reset_vault()
        config.wr_cfg({'workspaces':[]})
        self.ctx=PluginContext('calibration','Calibration',DOSSIER,{'permissions':['vault_write']})
        plugin.register(self.ctx)
        self.app=create_app(with_plugins=False)
        self.temps=patch.object(registre,'maintenant', return_value=datetime(2030,1,1,12,tzinfo=timezone.utc)).start()
        self.addCleanup(patch.stopall)
        self.o=objets.creer('prediction','Le service revient',dict(enonce='HTTP disponible', probabilite=.8,
            echeance='2030-01-08',critere_resolution='Un HTTP 200 constaté',domaine='Technique'))
        self.p=VAULT/self.o['chemin']

    def inscrire(self,h=OUVERTE):
        o=registre.inventaire(self.ctx)[0][0]
        return registre.inscrire(self.ctx,o['chemin'],h,o['version'])

    def resoudre(self,**champs):
        self.temps.return_value=datetime(2030,1,9,12,tzinfo=timezone.utc)
        return objets.modifier(self.o['cle'],self.o['titre'], dict(self.o['champs'],statut='resolue',
            resultat='oui',resolu_le='2030-01-09',preuve_resolution='Journal HTTP local',**champs))

    def test_copie_puis_resolution_et_export(self):
        copie=self.inscrire()
        self.assertEqual(registre.rapport(self.ctx)['global_']['n'],0)
        self.resoudre()
        r=registre.rapport(self.ctx)
        self.assertEqual(r['global_']['n'],1)
        self.assertAlmostEqual(r['global_']['brier'],.04)
        self.assertEqual(r['lignes'][0]['horizon_jours'],7)
        self.assertEqual(r['exclus'],[])
        with self.app.test_request_context(method='POST',json={}):
            reponse,code=self.ctx._dispatch('exporter')
        self.assertEqual(code,201)
        p=VAULT/reponse.get_json()['chemin']
        texte=p.read_text(encoding='utf-8'); meta=frontmatter.parse(texte)
        self.assertIn('Journal HTTP local',texte)
        self.assertIn('Classes de calibration',texte)
        self.assertIn('sans modèle',meta['prisme_genere_par'])
        self.assertIn('sans modèle',self.ctx.note_meta(VAULT/copie['copie'])['prisme_genere_par'])
        self.assertEqual(meta['prisme_outil'],'calibration')
        self.assertNotIn('brier',self.p.read_text(encoding='utf-8').lower())

    def test_sans_copie_exclu(self):
        self.resoudre()
        self.assertEqual(registre.rapport(self.ctx)['global_']['n'],0)
        with self.assertRaises(ValueError): self.inscrire()

    def test_pari_modifie_exclu(self):
        self.inscrire(); self.resoudre(probabilite=.9)
        r=registre.rapport(self.ctx)
        self.assertEqual(r['global_']['n'],0)
        self.assertIn('modifié',r['exclus'][0]['raison'])

    def test_inscription_ne_remplace_jamais(self):
        copie=VAULT/self.inscrire()['copie']; avant=copie.read_bytes()
        with self.assertRaises(ValueError): self.inscrire()
        with self.assertRaises(FileExistsError): self.ctx.write_note(copie,'autre',exclusive=True)
        self.assertEqual(copie.read_bytes(),avant)

    def test_version_perimee_necrit_pas(self):
        o=registre.inventaire(self.ctx)[0][0]; avant=self.p.read_text(encoding='utf-8')
        self.p.write_text(avant+'\nÉdition concurrente',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'changé'):
            registre.inscrire(self.ctx,o['chemin'],OUVERTE,o['version'])
        self.assertNotIn('prisme_valide_du',self.p.read_text(encoding='utf-8'))

    def test_horloge_invalide_necrit_pas(self):
        avant=self.p.read_bytes()
        with self.assertRaises(ValueError): self.inscrire({})
        self.assertEqual(self.p.read_bytes(),avant)
        self.assertFalse((VAULT/registre.DOSSIER).exists())

    def test_echeance_aujourdhui_refusee(self):
        self.temps.return_value=datetime(2030,1,8,tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError,'après aujourd'): self.inscrire()

    def test_copie_corrompue_exclue(self):
        p=VAULT/self.inscrire()['copie']; self.resoudre()
        p.write_text(frontmatter.update(p.read_text(encoding='utf-8'),{'prisme_calibration_sha256':'faux'}),encoding='utf-8')
        r=registre.rapport(self.ctx)
        self.assertEqual(r['global_']['n'],0)
        self.assertTrue(any('Empreinte' in e['raison'] for e in r['exclus']))

    def test_deux_copies_excluent_les_deux(self):
        p=VAULT/self.inscrire()['copie']; self.resoudre()
        shutil.copy2(p,p.with_name('doublon.md'))
        r=registre.rapport(self.ctx)
        self.assertEqual(r['global_']['n'],0)
        self.assertEqual(len(r['exclus']),2)

    def test_deux_objets_meme_id_exclus(self):
        self.inscrire(); self.resoudre(); shutil.copy2(self.p,VAULT/'double.md')
        self.assertEqual(registre.rapport(self.ctx)['global_']['n'],0)

    def test_copie_orpheline_exclue(self):
        self.inscrire(); self.p.unlink()
        self.assertEqual(registre.rapport(self.ctx)['global_']['n'],0)
        self.assertIn('absente',registre.rapport(self.ctx)['exclus'][0]['raison'])

    def test_filtre_monde_inconnu_exclu_mais_pas_sans_filtre(self):
        self.inscrire(INCONNUE); self.resoudre()
        self.assertEqual(registre.rapport(self.ctx)['global_']['n'],1)
        self.assertEqual(registre.rapport(self.ctx,'2030-01-03')['global_']['n'],0)
        self.assertIn('inconnue',registre.rapport(self.ctx,'2030-01-03')['exclus'][0]['raison'])

    def test_resolution_future_ou_indeterminable_exclue(self):
        self.inscrire(); self.resoudre()
        for changement in ({'resolu_le':'2030-01-10'},{'resultat':'indeterminable'}):
            champs=dict(self.o['champs'],statut='resolue',resultat='oui',resolu_le='2030-01-09',preuve_resolution='Preuve')
            objets.modifier(self.o['cle'],self.o['titre'],dict(champs,**changement))
            self.assertEqual(registre.rapport(self.ctx)['global_']['n'],0)

    def test_api_sans_plugin_garde_objets_sans_routes_score(self):
        self.inscrire()
        self.assertEqual(len(objets.lister('prediction')),1)
        self.assertFalse(any('calibration' in str(r) for r in self.app.url_map.iter_rules()))

    def test_chemin_hors_vault_et_permission(self):
        with self.assertRaises(PermissionError): registre.objet(self.ctx,str(TMP/'secret.md'))
        ctx=PluginContext('lecture','Lecture',DOSSIER,{})
        with self.assertRaises(PluginPermissionError): ctx.set_world_clock(self.p,OUVERTE)
        for v in (None,[],{}):
            with self.assertRaises(ValueError): registre.principal(self.ctx,v)

    def test_json_invalide(self):
        for route in ('inscrire','exporter'):
            with self.app.test_request_context(method='POST',json=[]):
                _,code=self.ctx._dispatch(route)
                self.assertEqual(code,400)
