"""Configurations pathologiques, table des antagonismes, et mise en fiche.

Trois choses sont vérifiées ici, et une quatrième ne l'est pas.

1. **La fidélité de la table** aux références : neuf paires, chacune fondée sur une
   citation, toutes portant sur des cartes existantes. Le contenu de la table n'est pas
   de notre ressort — il vient de `references/antagonismes.md` du dépôt NEXUS-ARCHÊ.
2. **Les invariants annoncés dans ces références** : aucun triangle, dix constellations
   en configuration 4, seize voisinages. Ce sont des affirmations publiées ; si le
   portage les contredit un jour, c'est le portage qui a bougé.
3. **Que confusion et antagonisme restent deux relations distinctes** — l'erreur que la
   table existe pour éviter. HIÉRARCHIE et RÉSEAU en sont le cas d'école.

Ce qui n'est pas testé : la justesse d'une configuration signalée. Elle dépend de la
question « ces structures portent-elles sur le même objet ? », à laquelle le code n'a
pas accès. C'est précisément pourquoi il pose la question au lieu de conclure.
"""
import importlib.util
import json
import sys
import unittest
from itertools import combinations

from commun import ROOT, VAULT, reset_vault, PLAFOND_FICHIER, taille_logique
from prisme_core import config
from prisme_core.app import create_app
from prisme_core.routes import security

DOSSIER = ROOT / 'plugins' / 'nexus-arche'
spec = importlib.util.spec_from_file_location(
    'nexus_cfg_test', DOSSIER / '__init__.py', submodule_search_locations=[str(DOSSIER)])
plugin = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugin
spec.loader.exec_module(plugin)
configurations = sys.modules['nexus_cfg_test.configurations']
catalogue = sys.modules['nexus_cfg_test.catalogue']
fiche = sys.modules['nexus_cfg_test.fiche']
sigma = sys.modules['nexus_cfg_test.sigma']

TIENT, BOUGE, MANQUE = configurations.TIENT, configurations.BOUGE, configurations.MANQUE

SITUATION = ("Le service a doublé ses effectifs en un an. Des pratiques de revue entre "
             "pairs se sont installées sans que personne ne les décide, et plus personne "
             "ne sait qui arbitre quoi. Personne ne sait ce que deviendra le service "
             "après la réorganisation annoncée.")


class Table(unittest.TestCase):
    def test_neuf_paires(self):
        self.assertEqual(len(configurations.toutes()), 9)

    def test_toutes_les_cartes_existent(self):
        for p in configurations.toutes():
            with self.subTest(paire=(p['a'], p['b'])):
                self.assertTrue(catalogue.existe(p['a']))
                self.assertTrue(catalogue.existe(p['b']))
                self.assertNotEqual(p['a'], p['b'])

    def test_chaque_paire_porte_un_fondement_et_un_statut(self):
        for p in configurations.toutes():
            with self.subTest(paire=(p['a'], p['b'])):
                self.assertIn(p['statut'], ('explicite', 'déduit'))
                self.assertGreater(len(p['fondement']), 40, 'un fondement, pas un mot')
                self.assertTrue(p['axe'].strip())

    def test_les_fondements_explicites_citent_les_references(self):
        """Statut « explicite » veut dire que l'incompatibilité est écrite dans
        `cards.md` — donc que le fondement contient une citation, pas un raisonnement."""
        for p in configurations.toutes():
            if p['statut'] == 'explicite':
                with self.subTest(paire=(p['a'], p['b'])):
                    self.assertIn('«', p['fondement'])

    def test_relation_symetrique(self):
        for p in configurations.toutes():
            self.assertEqual(configurations.antagonisme(p['a'], p['b']),
                             configurations.antagonisme(p['b'], p['a']))

    def test_une_carte_n_est_pas_son_propre_antagoniste(self):
        for c in catalogue.toutes():
            self.assertIsNone(configurations.antagonisme(c['id'], c['id']))

    def test_pas_de_triangle(self):
        """Annoncé dans les références, et c'est la raison pour laquelle la
        configuration 4 se déclenche à deux paires et non trois."""
        ids = [c['id'] for c in catalogue.toutes()]
        for trio in combinations(ids, 3):
            n = sum(1 for x, y in combinations(trio, 2) if configurations.antagonisme(x, y))
            self.assertLess(n, 3, trio)

    def test_dix_constellations_en_configuration_4(self):
        ids = [c['id'] for c in catalogue.toutes()]
        compte = sum(
            1 for trio in combinations(ids, 3)
            if sum(1 for x, y in combinations(trio, 2)
                   if configurations.antagonisme(x, y)) >= 2)
        self.assertEqual(compte, 10)

    def test_seize_voisinages(self):
        ids = [c['id'] for c in catalogue.toutes()]
        compte = sum(1 for a, b in combinations(ids, 2) if configurations.voisinage(a, b))
        self.assertEqual(compte, 16)


class ConfusionN_estPasAntagonisme(unittest.TestCase):
    """L'erreur que la table existe pour éviter."""

    def test_hierarchie_et_reseau_se_confondent_sans_s_exclure(self):
        self.assertIn('reseau', catalogue.confusions('hierarchie'))
        self.assertIsNone(configurations.antagonisme('hierarchie', 'reseau'))
        self.assertTrue(configurations.voisinage('hierarchie', 'reseau'))

    def test_reciprocite_et_hierarchie_s_excluent_sans_se_confondre(self):
        self.assertNotIn('hierarchie', catalogue.confusions('reciprocite'))
        self.assertIsNotNone(configurations.antagonisme('reciprocite', 'hierarchie'))

    def test_une_paire_antagoniste_n_est_jamais_un_voisinage(self):
        """Deux structures incompatibles ne sont pas « de même nature », même proches."""
        for p in configurations.toutes():
            with self.subTest(paire=(p['a'], p['b'])):
                self.assertFalse(configurations.voisinage(p['a'], p['b']))


class Detection(unittest.TestCase):
    def test_aucune_configuration_par_defaut(self):
        """La table est creuse : neuf paires sur 120, seize voisinages. Une
        constellation ordinaire ne déclenche rien, et c'est la règle."""
        self.assertEqual(configurations.detecter(
            {TIENT: 'seuil', BOUGE: 'reciprocite', MANQUE: 'recursivite'}), [])

    def test_configuration_1_miroir(self):
        s = configurations.detecter({TIENT: 'seuil', BOUGE: 'reseau', MANQUE: 'seuil'})
        self.assertEqual([x['numero'] for x in s], [1])

    def test_configuration_2_voisinage(self):
        s = configurations.detecter({TIENT: 'hierarchie', BOUGE: 'reseau', MANQUE: 'polarite'})
        self.assertEqual([x['numero'] for x in s], [2])
        self.assertTrue(s[0]['fragile'], 'le voisinage est une définition dérivée')

    def test_configuration_3_lacune_contradictoire(self):
        s = configurations.detecter({TIENT: 'seuil', BOUGE: 'reseau', MANQUE: 'transformation'})
        self.assertEqual([x['numero'] for x in s], [3])
        self.assertEqual(s[0]['question'], configurations.MEME_OBJET)
        self.assertIn('«', s[0]['fondement'])

    def test_configuration_3_est_positionnelle(self):
        """L'antagonisme est symétrique, la configuration ne l'est pas : elle porte sur
        « ce qui tient » et « ce qui manque », pas sur deux cartes quelconques."""
        s = configurations.detecter({TIENT: 'seuil', BOUGE: 'transformation', MANQUE: 'reseau'})
        self.assertNotIn(3, [x['numero'] for x in s])

    def test_configuration_4_tension_maximale(self):
        s = configurations.detecter(
            {TIENT: 'emergence', BOUGE: 'incertitude', MANQUE: 'croissance'})
        numeros = [x['numero'] for x in s]
        self.assertIn(4, numeros)
        quatre = [x for x in s if x['numero'] == 4][0]
        self.assertEqual(len(quatre['paires']), 2)

    def test_une_seule_paire_ne_suffit_pas_pour_la_4(self):
        s = configurations.detecter({TIENT: 'seuil', BOUGE: 'reseau', MANQUE: 'transformation'})
        self.assertNotIn(4, [x['numero'] for x in s])

    def test_carte_inactive_n_entre_dans_aucune_configuration(self):
        """Une carte tirée sans ancrage est déclarée inactive : sa position est vide, et
        rien ne peut être prononcé dessus."""
        actives, inactives = configurations.positions_actives(
            [{'id': 'seuil'}],
            [{'id': 'seuil', 'position': TIENT}, {'id': 'transformation', 'position': MANQUE}])
        self.assertEqual(actives, {TIENT: 'seuil'})
        self.assertEqual(inactives, [MANQUE])
        self.assertEqual(configurations.detecter(actives), [])

    def test_sans_position_aucune_configuration(self):
        """Le mode où le modèle choisit les cartes ne produit pas de constellation."""
        actives, inactives = configurations.positions_actives(
            [{'id': 'seuil'}, {'id': 'transformation'}],
            [{'id': 'seuil', 'position': ''}, {'id': 'transformation', 'position': ''}])
        self.assertEqual(actives, {})
        self.assertEqual(configurations.detecter(actives), [])


class Fiche(unittest.TestCase):
    def donnees(self, **extra):
        d = {'situation': SITUATION, 'mode_nom': 'Constellation',
             'retenues': [
                 {'id': 'croissance', 'ancrage': 'doublé ses effectifs en un an',
                  'position': TIENT, 'anti_resonance': 'la courbe peut avoir saturé'},
                 {'id': 'incertitude', 'position': BOUGE,
                  'ancrage': 'Personne ne sait ce que deviendra le service'},
                 {'id': 'emergence', 'ancrage': 'sans que personne ne les décide',
                  'position': MANQUE}],
             'ecartees': [{'id': 'reseau', 'motif': 'ancrage introuvable dans la situation'}]}
        d.update(extra)
        return d

    def test_consolidation_et_configurations(self):
        p, e = fiche.consolider(self.donnees())
        self.assertIsNone(e)
        self.assertEqual([x['numero'] for x in p['configurations']], [3, 4])

    def test_ancrage_faux_bloque_l_ecriture(self):
        """Une fiche est ce qui survit à la séance : elle ne doit pas pouvoir contenir
        une citation qui n'en est pas une, même si l'interface l'affichait."""
        d = self.donnees()
        d['retenues'][0]['ancrage'] = "l'équipe a grandi très vite cette année"
        p, e = fiche.consolider(d)
        self.assertIsNone(p)
        self.assertIn('CROISSANCE', e)
        self.assertIn('citation', e)

    def test_nom_de_carte_relu_au_catalogue(self):
        """Le nom affiché ne fait pas foi : il est relu depuis l'identifiant."""
        d = self.donnees()
        d['retenues'][0]['nom'] = 'LICORNE'
        p, _ = fiche.consolider(d)
        self.assertEqual(p['retenues'][0]['nom'], 'CROISSANCE')

    def test_carte_inconnue_refusee(self):
        d = self.donnees()
        d['retenues'][0]['id'] = 'licorne'
        p, e = fiche.consolider(d)
        self.assertIsNone(p)
        self.assertIn('licorne', e)

    def test_deux_cartes_sur_une_meme_position_refusees(self):
        d = self.donnees()
        d['retenues'][1]['position'] = TIENT
        p, e = fiche.consolider(d)
        self.assertIsNone(p)
        self.assertIn('position', e.lower())

    def test_chaine_nexus_suit_les_positions(self):
        """`tient.bouge.manque` est une syntaxe positionnelle : l'ordre porte le sens."""
        p, _ = fiche.consolider(self.donnees())
        glyphes, transcription = fiche.chaine_nexus(p['retenues'])
        self.assertEqual(glyphes, '▲Ø⊙')
        self.assertEqual(transcription, 'INTENSITÉ.VIDE.SOURCE')

    def test_chaine_nexus_n_est_pas_une_signature_sigma(self):
        """Les deux alphabets partagent des glyphes avec des sens différents. Soumettre
        la chaîne des cartes au valideur Σ est exactement ce qu'il faut ne jamais faire —
        ce test dit que le résultat n'aurait aucun sens, pas qu'il est interdit."""
        p, _ = fiche.consolider(self.donnees())
        glyphes, transcription = fiche.chaine_nexus(p['retenues'])
        verdict = sigma.valider(glyphes, exiger_statut=False)
        self.assertNotEqual(verdict.get('transcription'), transcription)

    def test_signature_invalide_bloque_l_ecriture(self):
        p, e = fiche.consolider(self.donnees(signature='⟦◐⊙⊜⟧ Clos'))
        self.assertIsNone(p)
        self.assertIn('MÉMOIRE-Σ', e)

    def test_signature_valide_transcrite(self):
        p, e = fiche.consolider(self.donnees(signature='⟦⊙∿◯⊜⟧ Clos'))
        self.assertIsNone(e)
        self.assertIn('SOURCE.MOUVEMENT.FORME.SCELLER', p['transcription_sigma'])

    def test_format_inconnu_refuse(self):
        p, _ = fiche.consolider(self.donnees())
        with self.assertRaises(ValueError):
            fiche.markdown(p, 'pdf')

    def test_fiche_longue_garde_tout(self):
        p, _ = fiche.consolider(self.donnees(statut='descriptif'))
        md = fiche.markdown(p, 'longue')
        self.assertIn(SITUATION[:40], md)
        self.assertIn('Anti-résonance', md)
        self.assertIn('À trancher vous-même', md)
        self.assertIn('Descriptif', md)
        self.assertIn('ne prédit pas', md)

    def test_bloc_condense_garde_les_ancrages_et_les_reserves(self):
        """Condensé ne veut pas dire sans preuve ni sans réserve : une fiche archivée
        sans elles finit par se lire comme un verdict."""
        p, _ = fiche.consolider(self.donnees())
        md = fiche.markdown(p, 'bloc')
        self.assertIn('doublé ses effectifs en un an', md)
        self.assertIn('ne prédit pas', md)
        self.assertNotIn(SITUATION[:40], md)
        self.assertLess(len(md), len(fiche.markdown(p, 'longue')))

    def test_les_deux_formats_signalent_la_configuration_comme_une_question(self):
        p, _ = fiche.consolider(self.donnees())
        for f in ('longue', 'bloc'):
            with self.subTest(format=f):
                md = fiche.markdown(p, f)
                self.assertIn('Tension maximale', md)
                self.assertIn(configurations.MEME_OBJET, md)


class Routes(unittest.TestCase):
    def setUp(self):
        reset_vault()
        config.wr_cfg({'workspaces': []})
        self.c = create_app().test_client()
        self.h = {'X-Prisme-Token': security.TOKEN}

    def post(self, url, corps):
        return self.c.post('/api/plugins/nexus-arche' + url, json=corps, headers=self.h)

    def charge(self, **extra):
        d = {'situation': SITUATION, 'format': 'longue',
             'retenues': [{'id': 'croissance', 'ancrage': 'doublé ses effectifs en un an',
                           'position': TIENT},
                          {'id': 'emergence', 'ancrage': 'sans que personne ne les décide',
                           'position': MANQUE}],
             'ecartees': []}
        d.update(extra)
        return d

    def test_etat_annonce_les_formats(self):
        d = self.c.get('/api/plugins/nexus-arche/etat', headers=self.h).get_json()
        self.assertIn('longue', d['formats'])
        self.assertIn('bloc', d['formats'])
        self.assertIn('descriptif', d['statuts'])

    def test_fiche_ecrite_dans_le_vault(self):
        r = self.post('/fiche', self.charge())
        self.assertEqual(r.status_code, 201)
        chemin = VAULT / r.get_json()['chemin']
        self.assertTrue(chemin.exists())
        texte = chemin.read_text(encoding='utf-8')
        self.assertIn('doublé ses effectifs en un an', texte)
        self.assertIn('Lacune active contradictoire', texte)

    def test_fiche_refusee_si_un_ancrage_n_est_pas_une_citation(self):
        c = self.charge()
        c['retenues'][0]['ancrage'] = 'le service a beaucoup grandi'
        r = self.post('/fiche', c)
        self.assertEqual(r.status_code, 400)
        self.assertFalse(list((VAULT / 'Lectures NEXUS').glob('*.md'))
                         if (VAULT / 'Lectures NEXUS').exists() else [])

    def test_corps_non_json_refuse(self):
        r = self.c.post('/api/plugins/nexus-arche/fiche', data='oui',
                        content_type='text/plain', headers=self.h)
        self.assertEqual(r.status_code, 400)

    def test_jeton_exige(self):
        r = self.c.post('/api/plugins/nexus-arche/fiche', json=self.charge())
        self.assertEqual(r.status_code, 403)


class Structure(unittest.TestCase):
    def test_aucun_fichier_monolithique(self):
        for f in list(DOSSIER.glob('*.py')) + list(DOSSIER.glob('ui.*')):
            with self.subTest(fichier=f.name):
                self.assertLess(taille_logique(f), PLAFOND_FICHIER, f.name)

    def test_la_table_est_un_fichier_de_donnees(self):
        """Comme les cartes : les références ne sont jamais recopiées dans du code."""
        d = json.loads((DOSSIER / 'antagonismes.json').read_text(encoding='utf-8'))
        self.assertIn('antagonismes.md', d['source'])
        self.assertEqual(len(d['paires']), 9)


if __name__ == '__main__':
    unittest.main()
