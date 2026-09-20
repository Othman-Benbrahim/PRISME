"""Lecture assistée : ce que le plugin fait quand le modèle répond MAL.

On ne teste pas la justesse d'une lecture — on n'y a pas accès, et elle dépend d'un
modèle. On teste les garde-fous, et ils sont tous vérifiables hors ligne avec un appel
simulé. C'est là qu'est le risque réel dès lors que le modèle est au centre.

Le garde-fou central : **l'ancrage doit être une citation littérale**. Sans lui, le même
modèle propose la carte et rédige la preuve qui la justifie.
"""
import importlib.util
import json
import sys
import unittest

from commun import ROOT

DOSSIER = ROOT / 'plugins' / 'nexus-arche'
spec = importlib.util.spec_from_file_location(
    'nexus_lec_test', DOSSIER / '__init__.py', submodule_search_locations=[str(DOSSIER)])
plugin = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugin
spec.loader.exec_module(plugin)
lecture = sys.modules['nexus_lec_test.lecture']
tirage = sys.modules['nexus_lec_test.tirage']
catalogue = sys.modules['nexus_lec_test.catalogue']

SITUATION = ("Après douze ans dans l'entreprise, elle a remis sa lettre de démission lundi. "
             "Le contrat avec le nouvel employeur est signé. Le préavis court encore deux mois, "
             "et l'équipe n'a pas été informée.")


class FauxCtx:
    """Un `ctx` réduit à ce que `lecture.proposer` utilise : l'appel au modèle."""

    def __init__(self, reponse=None, erreur=None):
        self.reponse, self.erreur, self.appels = reponse, erreur, []

    def ai_call(self, messages, **kw):
        self.appels.append((messages, kw))
        return self.reponse, self.erreur


def reponse(cartes):
    return json.dumps({'cartes': cartes}, ensure_ascii=False)


class AncrageLitteral(unittest.TestCase):
    def test_citation_exacte_acceptee(self):
        ok, _ = lecture.ancrage_litteral(SITUATION, "elle a remis sa lettre de démission lundi")
        self.assertTrue(ok)

    def test_variations_typographiques_tolerees(self):
        """Le modèle recopie rarement au caractère près : apostrophe courbe, espaces,
        accents perdus. Ce sont des variations de forme, pas de contenu."""
        for variante in ["elle a remis sa lettre de demission lundi",
                         "elle  a remis sa   lettre de démission lundi",
                         "L'ÉQUIPE N'A PAS ÉTÉ INFORMÉE",
                         "l’équipe n’a pas été informée"]:
            with self.subTest(variante=variante):
                self.assertTrue(lecture.ancrage_litteral(SITUATION, variante)[0], variante)

    def test_paraphrase_refusee(self):
        """Le cœur du dispositif : une justification plausible mais inventée ne passe pas."""
        for faux in ["elle quitte son poste après une longue période",
                     "la rupture est irréversible",
                     "un changement de vie majeur est engagé"]:
            with self.subTest(faux=faux):
                ok, raison = lecture.ancrage_litteral(SITUATION, faux)
                self.assertFalse(ok, faux)
                self.assertIn('citation', raison)

    def test_extrait_trop_court_refuse(self):
        """Sans longueur minimale, « le » serait un ancrage valide."""
        ok, raison = lecture.ancrage_litteral(SITUATION, "lundi")
        self.assertFalse(ok)
        self.assertIn('trop court', raison)

    def test_ancrage_vide(self):
        self.assertFalse(lecture.ancrage_litteral(SITUATION, '')[0])


class GardeFous(unittest.TestCase):
    def lire(self, cartes, imposees=None, situation=SITUATION):
        ctx = FauxCtx(reponse(cartes))
        r, e = lecture.proposer(ctx, situation, imposees)
        self.assertIsNone(e, e)
        return r

    def test_lecture_nominale(self):
        r = self.lire([
            {'id': 'seuil', 'ancrage': 'Le contrat avec le nouvel employeur est signé',
             'anti_resonance': 'Le préavis court encore : rien n\'est consommé.'},
            {'id': 'transformation', 'ancrage': "Après douze ans dans l'entreprise",
             'anti_resonance': 'Aucune mutation progressive décrite.'}])
        self.assertEqual([c['id'] for c in r['retenues']], ['seuil', 'transformation'])
        self.assertEqual(r['ecartees'], [])

    def test_carte_sans_ancrage_litteral_ecartee_mais_visible(self):
        """« Une carte sans ancrage est une carte inactive — elle ne disparaît pas. »"""
        r = self.lire([
            {'id': 'seuil', 'ancrage': 'Le contrat avec le nouvel employeur est signé'},
            {'id': 'reseau', 'ancrage': "l'équipe est un réseau de relations fragilisé"}])
        self.assertEqual([c['id'] for c in r['retenues']], ['seuil'])
        self.assertEqual(r['ecartees'][0]['id'], 'reseau')
        self.assertIn('citation', r['ecartees'][0]['motif'])
        self.assertIn('ancrage_refuse', r['ecartees'][0])

    def test_plus_de_trois_cartes_ecretees(self):
        """« 2 à 3 candidates, jamais plus. » Un modèle bavard ne doit pas élargir la lecture."""
        a = "Le préavis court encore deux mois"
        r = self.lire([{'id': i, 'ancrage': a} for i in
                       ('seuil', 'transformation', 'contrainte', 'periodicite')])
        self.assertEqual(len(r['retenues']), 3)
        self.assertIn('au-delà', r['ecartees'][0]['motif'])
        self.assertIn('plus de 3', r['avertissement'])

    def test_carte_inventee_refusee(self):
        r = self.lire([{'id': 'synchronicite', 'ancrage': 'Le préavis court encore deux mois'}])
        self.assertEqual(r['retenues'], [])
        self.assertIn('inconnue', r['ecartees'][0]['motif'])

    def test_doublon_refuse(self):
        a = 'Le préavis court encore deux mois'
        r = self.lire([{'id': 'seuil', 'ancrage': a}, {'id': 'seuil', 'ancrage': a}])
        self.assertEqual(len(r['retenues']), 1)
        self.assertIn('deux fois', r['ecartees'][0]['motif'])

    def test_aucune_carte_ancree_est_un_resultat(self):
        r = self.lire([{'id': 'reseau', 'ancrage': 'tout est connecté à tout'}])
        self.assertEqual(r['retenues'], [])
        self.assertIn("pas un échec", r['avertissement'])

    def test_cartes_imposees_respectees(self):
        """En tirage aléatoire, le modèle cherche un ancrage : il ne choisit pas la carte."""
        r = self.lire([{'id': 'seuil', 'ancrage': 'Le préavis court encore deux mois'},
                       {'id': 'croissance', 'ancrage': 'Le préavis court encore deux mois'}],
                      imposees=['seuil'])
        self.assertEqual([c['id'] for c in r['retenues']], ['seuil'])
        self.assertIn('hors des cartes tirées', r['ecartees'][0]['motif'])


class ReponsesMalformees(unittest.TestCase):
    def test_json_noye_dans_du_texte(self):
        ctx = FauxCtx('Voici mon analyse :\n```json\n' + reponse(
            [{'id': 'seuil', 'ancrage': 'Le préavis court encore deux mois'}]) + '\n```\nVoilà.')
        r, e = lecture.proposer(ctx, SITUATION)
        self.assertIsNone(e)
        self.assertEqual(len(r['retenues']), 1)

    def test_json_illisible(self):
        r, e = lecture.proposer(FauxCtx('je ne peux pas répondre'), SITUATION)
        self.assertIsNone(r)
        self.assertIn('illisible', e)

    def test_reponse_vide(self):
        r, e = lecture.proposer(FauxCtx(''), SITUATION)
        self.assertIsNone(r)

    def test_liste_absente(self):
        r, e = lecture.proposer(FauxCtx('{"resultat": "rien"}'), SITUATION)
        self.assertEqual(r['retenues'], [])
        self.assertIn('liste', r['avertissement'])

    def test_ia_indisponible_remontee_telle_quelle(self):
        r, e = lecture.proposer(FauxCtx(None, 'Clé API manquante'), SITUATION)
        self.assertIsNone(r)
        self.assertEqual(e, 'Clé API manquante')

    def test_situation_trop_courte_ne_consulte_pas_le_modele(self):
        ctx = FauxCtx(reponse([]))
        r, e = lecture.proposer(ctx, 'trop court')
        self.assertIsNone(r)
        self.assertEqual(ctx.appels, [], 'le modèle ne doit pas être appelé pour rien')


class Tirage(unittest.TestCase):
    def test_les_trois_modes(self):
        for mode, n in ((1, 1), (2, 2), (3, 3)):
            with self.subTest(mode=mode):
                t = tirage.tirer(mode)
                self.assertEqual(len(t['cartes']), n)
                for c in t['cartes']:
                    self.assertTrue(catalogue.existe(c['id']))

    def test_pas_de_doublon_dans_une_constellation(self):
        for _ in range(40):
            ids = [c['id'] for c in tirage.tirer(3)['cartes']]
            self.assertEqual(len(set(ids)), 3)

    def test_positions_de_la_constellation(self):
        self.assertEqual([c['position'] for c in tirage.tirer(3)['cartes']],
                         ['ce qui tient', 'ce qui bouge', 'ce qui manque'])

    def test_mode_inconnu(self):
        with self.assertRaises(ValueError):
            tirage.tirer(4)

    def test_toutes_les_cartes_sortent_a_la_longue(self):
        """Un tirage qui ne couvrirait pas le catalogue trahirait un biais."""
        vues = set()
        for _ in range(400):
            vues.update(c['id'] for c in tirage.tirer(3)['cartes'])
        self.assertEqual(len(vues), 16)


class Distinctions(unittest.TestCase):
    def test_questions_entre_cartes_retenues(self):
        q = lecture.questions_de_distinction(
            [{'id': 'seuil'}, {'id': 'transformation'}])
        self.assertTrue(q)
        self.assertIn('?', q[0]['critere'])

    def test_aucune_question_pour_une_seule_carte(self):
        self.assertEqual(lecture.questions_de_distinction([{'id': 'seuil'}]), [])


if __name__ == '__main__':
    unittest.main()
