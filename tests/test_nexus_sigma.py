"""Valideur de signature MÉMOIRE-Σ : le seul critère formel du plugin.

Une grammaire qu'on assouplit dès qu'elle refuse quelque chose cesse d'être un critère.
Ces tests fixent donc autant ce qui est REFUSÉ que ce qui passe — et notamment le refus
d'un glyphe du catalogue NEXUS, qui partage l'alphabet sans partager les sens.
"""
import importlib.util
import sys
import unittest

from commun import ROOT

DOSSIER = ROOT / 'plugins' / 'nexus-arche'
spec = importlib.util.spec_from_file_location(
    'nexus_sigma_test', DOSSIER / '__init__.py', submodule_search_locations=[str(DOSSIER)])
plugin = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugin
spec.loader.exec_module(plugin)
sigma = sys.modules['nexus_sigma_test.sigma']
catalogue = sys.modules['nexus_sigma_test.catalogue']


class Alphabet(unittest.TestCase):
    def test_vingt_primitives_en_trois_strates(self):
        """Le README annonçait 25 en 4 strates : c'est l'alphabet de STÈLE, pas celui
        que MÉMOIRE-Σ embarque. Le décompte est figé ici pour que l'écart ne revienne pas."""
        self.assertEqual((len(sigma.SUBSTANCES), len(sigma.OPERATIVES), len(sigma.MODALES)),
                         (8, 7, 5))

    def test_aucun_glyphe_dans_deux_strates(self):
        tous = list(sigma.SUBSTANCES) + list(sigma.OPERATIVES) + list(sigma.MODALES)
        self.assertEqual(len(tous), len(set(tous)))


class Valides(unittest.TestCase):
    def test_les_exemples_canoniques_du_skill(self):
        for chaine, attendu in [
            ('⟦⊙∿◯⊜⟧ Clos', 'SOURCE.MOUVEMENT.FORME.SCELLER'),
            ('⟦Ø✶⥀◐⟧ Bifurqué', 'VIDE.RÉVÉLER.INVERSER.CONDITIONNEL'),
            ('⟦◊⊛◯⟁↻⟧ Clos', 'TRACE.NOEUD.FORME.FRACTURER.CYCLE'),
            ('⟦⊙∿⊛⟁◐⟧ Ouvert', 'SOURCE.MOUVEMENT.NOEUD.FRACTURER.CONDITIONNEL'),
        ]:
            with self.subTest(chaine=chaine):
                r = sigma.valider(chaine)
                self.assertTrue(r['ok'], r['raison'])
                self.assertEqual(r['transcription'], attendu)

    def test_minimum_une_substance_une_operative(self):
        self.assertTrue(sigma.valider('⟦⊥⊗⟧ Clos')['ok'])

    def test_statut_facultatif_a_la_demande(self):
        """L'interface valide la chaîne avant que l'auteur ait choisi le statut."""
        self.assertTrue(sigma.valider('⟦⊙⊜⟧', exiger_statut=False)['ok'])
        self.assertFalse(sigma.valider('⟦⊙⊜⟧')['ok'])

    def test_chaine_nue_acceptee(self):
        self.assertTrue(sigma.valider('⊙⊜', exiger_statut=False)['ok'])


class Refuses(unittest.TestCase):
    def refus(self, chaine, extrait):
        r = sigma.valider(chaine)
        self.assertFalse(r['ok'], 'aurait dû être refusée : %s' % chaine)
        self.assertIn(extrait, r['raison'])
        return r

    def test_ordre_des_strates_rompu(self):
        self.refus('⟦◐⊙⊜⟧ Clos', 'Ordre des strates')
        self.refus('⟦⊙⊜◯⟧ Clos', 'Ordre des strates')

    def test_comptes_hors_bornes(self):
        self.refus('⟦⊙⊛◯✦⟁⟧ Clos', '4 substances')
        self.refus('⟦⊙⟧ Clos', 'au moins 1 opérative')
        self.refus('⟦⊙⟁⊗⟶⟧ Clos', '3 opératives')

    def test_plafond_de_six_glyphes(self):
        self.refus('⟦⊙∿◯⟁⊗↻▲⟧ Clos', 'maximum est 6')

    def test_glyphe_du_catalogue_nexus_refuse(self):
        """`↺` RÉCURSIVITÉ est une carte NEXUS et n'appartient pas à MÉMOIRE-Σ.

        Les deux alphabets se recouvrent sans se confondre : `⊥` vaut LIMITE ici et
        SEUIL au catalogue. Laisser passer un glyphe étranger produirait une signature
        qui se lit de deux façons.
        """
        r = self.refus('⟦⊙↺⊜⟧ Clos', 'hors alphabet')
        self.assertIn('↺', r['raison'])

    def test_delimiteurs(self):
        self.refus('⟦⊙⊜ Clos', 'fermant')
        self.refus('⊙⊜⟧ Clos', 'ouvrant')
        self.refus('bruit ⟦⊙⊜⟧ Clos', 'avant le délimiteur')

    def test_statut(self):
        self.refus('⟦⊙⊜⟧', 'Statut manquant')
        self.refus('⟦⊙⊜⟧ Fini', 'Statut inconnu')

    def test_vide(self):
        self.refus('⟦⟧ Clos', 'vide')
        self.refus('', 'vide')


class Frontiere(unittest.TestCase):
    def test_aucun_glyphe_nexus_hors_sigma_ne_passe(self):
        """Balayage complet : toute carte du catalogue absente de l'alphabet Σ est refusée."""
        etrangers = [g for g in catalogue.glyphes() if sigma.strate(g) is None]
        self.assertTrue(etrangers, 'les deux alphabets devraient différer')
        for g in etrangers:
            with self.subTest(glyphe=g):
                self.assertFalse(sigma.valider('⟦⊙%s⊜⟧ Clos' % g)['ok'])

    def test_les_glyphes_communs_ne_disent_pas_la_meme_chose(self):
        """Le piège à documenter : `⊥` est LIMITE en Σ, SEUIL au catalogue."""
        self.assertEqual(sigma.mot('⊥'), 'LIMITE')
        self.assertEqual(catalogue.par_id('seuil')['nom'], 'SEUIL')


if __name__ == '__main__':
    unittest.main()
