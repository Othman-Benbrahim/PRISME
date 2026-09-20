"""Fidélité du catalogue aux références, et routes du lot 1.

Le catalogue est une COPIE de `references/cards.md` du dépôt NEXUS-ARCHÊ. Ces tests
vérifient qu'elle est complète et cohérente ; ils ne jugent pas le contenu, qui n'est
pas de notre ressort.
"""
import importlib.util
import json
import sys
import unittest

from commun import ROOT, VAULT, reset_vault, PLAFOND_FICHIER, taille_logique
from prisme_core import config
from prisme_core.app import create_app
from prisme_core.routes import security

DOSSIER = ROOT / 'plugins' / 'nexus-arche'
spec = importlib.util.spec_from_file_location(
    'nexus_cat_test', DOSSIER / '__init__.py', submodule_search_locations=[str(DOSSIER)])
plugin = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugin
spec.loader.exec_module(plugin)
catalogue = sys.modules['nexus_cat_test.catalogue']

ATTENDUES = ['SEUIL', 'RÉCIPROCITÉ', 'PÉRIODICITÉ', 'RÉCURSIVITÉ', 'ÉMERGENCE',
             'HIÉRARCHIE', 'RÉSEAU', 'POLARITÉ', 'INCERTITUDE', 'CONTRAINTE',
             'PROPORTION', 'TRANSFORMATION', 'TRACE · MÉMOIRE', 'CROISSANCE',
             'COMMUNAUTÉ', 'RÉSONANCE']


class Fidelite(unittest.TestCase):
    def test_seize_cartes_nommees(self):
        self.assertEqual([c['nom'] for c in catalogue.toutes()], ATTENDUES)

    def test_aucun_champ_vide(self):
        for c in catalogue.toutes():
            for cle in ('id', 'nom', 'glyphe', 'mot', 'registre_rationnel',
                        'registre_symbolique', 'branche_math', 'question_iris', 'stele'):
                with self.subTest(carte=c['nom'], champ=cle):
                    self.assertTrue(c[cle].strip())

    def test_identifiants_et_glyphes_uniques(self):
        cartes = catalogue.toutes()
        self.assertEqual(len({c['id'] for c in cartes}), 16)
        self.assertEqual(len({c['glyphe'] for c in cartes}), 16)

    def test_identifiants_sans_accent_ni_espace(self):
        """Ils servent de clés d'URL et de noms de fichiers : ASCII strict."""
        for c in catalogue.toutes():
            with self.subTest(carte=c['nom']):
                self.assertRegex(c['id'], r'^[a-z0-9-]+$')

    def test_chaque_carte_a_ses_distinctions(self):
        for c in catalogue.toutes():
            with self.subTest(carte=c['nom']):
                self.assertTrue(c['distinctions'])

    def test_les_distinctions_pointent_vers_des_cartes_existantes(self):
        """Une distinction qui désigne une carte inconnue casserait l'arbre de questions."""
        for c in catalogue.toutes():
            for d in c['distinctions']:
                with self.subTest(carte=c['nom'], autre=d['autre']):
                    self.assertTrue(catalogue.existe(d['autre']))
                    self.assertNotEqual(d['autre'], c['id'])

    def test_chaque_distinction_porte_un_critere(self):
        for c in catalogue.toutes():
            for d in c['distinctions']:
                with self.subTest(carte=c['nom'], autre=d['autre']):
                    self.assertTrue(d['critere'].strip())

    def test_questions_entre_deux_cartes(self):
        q = catalogue.questions_entre('seuil', 'transformation')
        self.assertTrue(q)
        for item in q:
            self.assertIn('?', item['critere'])

    def test_questions_entre_cartes_sans_rapport(self):
        self.assertEqual(catalogue.questions_entre('seuil', 'seuil'), [])


class Structure(unittest.TestCase):
    def test_les_donnees_ne_sont_pas_dans_le_code(self):
        """`cards.md` fait plus de 20 000 caractères : porté dans un module Python, il
        ferait sauter à lui seul la règle « aucun fichier monolithique » (0005)."""
        for f in DOSSIER.glob('*.py'):
            with self.subTest(fichier=f.name):
                self.assertLess(taille_logique(f), PLAFOND_FICHIER, f.name)
        self.assertGreater(taille_logique(DOSSIER / 'cartes.json'), PLAFOND_FICHIER)

    def test_manifest_conforme(self):
        m = json.loads((DOSSIER / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(m['id'], 'nexus-arche')
        self.assertEqual(m['id'], DOSSIER.name)
        self.assertEqual(m['api_version'], 1)
        self.assertEqual(m['permissions'], ['vault_write'])
        self.assertNotIn('network', m['permissions'])
        self.assertNotIn('secrets', m)


class Routes(unittest.TestCase):
    def setUp(self):
        reset_vault()
        config.wr_cfg({'workspaces': []})
        self.c = create_app().test_client()
        self.h = {'X-Prisme-Token': security.TOKEN}

    def get(self, url):
        return self.c.get('/api/plugins/nexus-arche' + url, headers=self.h)

    def post(self, url, corps):
        return self.c.post('/api/plugins/nexus-arche' + url, json=corps, headers=self.h)

    def test_catalogue(self):
        d = self.get('/catalogue').get_json()
        self.assertEqual(d['total'], 16)
        self.assertEqual(d['cartes'][0]['nom'], 'SEUIL')

    def test_jeton_exige(self):
        self.assertEqual(self.c.get('/api/plugins/nexus-arche/catalogue').status_code, 403)

    def test_distinctions(self):
        d = self.get('/distinctions?a=seuil&b=transformation').get_json()
        self.assertTrue(d['questions'])

    def test_carte_inconnue_refusee(self):
        r = self.get('/distinctions?a=seuil&b=licorne')
        self.assertEqual(r.status_code, 400)

    def test_valider_signature(self):
        d = self.post('/valider_signature', {'chaine': '⟦⊙∿◯⊜⟧ Clos'}).get_json()
        self.assertTrue(d['ok'])
        self.assertEqual(d['transcription'], 'SOURCE.MOUVEMENT.FORME.SCELLER')

    def test_signature_refusee_rend_une_raison(self):
        d = self.post('/valider_signature', {'chaine': '⟦◐⊙⊜⟧ Clos'}).get_json()
        self.assertFalse(d['ok'])
        self.assertIn('Ordre des strates', d['raison'])

    def test_corps_non_json_refuse(self):
        r = self.c.post('/api/plugins/nexus-arche/valider_signature',
                        data='pas du json', headers=self.h)
        self.assertEqual(r.status_code, 400)

    def test_glyphes_intacts_sur_tout_le_trajet(self):
        """Aller-retour HTTP complet : les glyphes ne doivent pas être échappés ni
        transcodés. La machine cible est Windows, et aucun de ces signes n'existe
        en cp1252."""
        d = self.get('/catalogue').get_json()
        self.assertEqual(d['cartes'][0]['glyphe'], '⊥')
        brut = self.get('/catalogue').get_data(as_text=True)
        self.assertNotIn('\\u22a5', brut)


if __name__ == '__main__':
    unittest.main()
