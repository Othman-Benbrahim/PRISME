"""E11 : formats utiles, refus, validation humaine et isolation du vault."""
import unittest
from pathlib import Path

from commun import TMP, VAULT, reset_vault
from prisme_core import config, frontmatter
from prisme_core.app import create_app
from prisme_core.objets import balayage, file, registre, reglages, sources, types
from prisme_core.routes import security

EXEMPLES = {
    "decision": {"choix": "Garder Markdown", "justification": "Lisible sans PRISME"},
    "hypothese": {"enonce": "Le service est indisponible", "critere_refutation": "Une réponse HTTP valide"},
    "prediction": {"enonce": "Le service sera rétabli", "probabilite": 0.7,
                   "echeance": "2027-01-02", "critere_resolution": "HTTP 200 à 12h UTC"},
    "entite": {"nature": "organisation", "description": "Organisation de recherche"},
    "tache": {"action": "Rédiger le guide", "critere_fin": "Guide relu par l'auteur"},
}


class E11Base(unittest.TestCase):
    def setUp(self):
        reset_vault()
        config.wr_cfg({"objets_types": {}, "workspaces": []})
        file._ecrire({"entrees": [], "rejets": {}})
        self.client = create_app(with_plugins=False).test_client()
        self.h = {"X-Prisme-Token": security.TOKEN}

    def post(self, route, data):
        return self.client.post(route, json=data, headers=self.h)

    def agent(self, droits=None):
        from prisme_core.agents import cles
        cles._ecrire({})
        r = self.post('/api/agents/cles', {"nom": "Constat", "droits": droits or ["lecture", "proposition"]})
        return {"X-Prisme-Cle": r.get_json()["cle"]}


class TestFormats(E11Base):
    def test_cinq_types_notes_portables_et_estampillees(self):
        for t, champs in EXEMPLES.items():
            with self.subTest(type=t):
                o = registre.creer(t, 'Essai « été » ' + t, champs)
                p = VAULT / o['chemin']
                contenu = p.read_text(encoding='utf-8')
                meta = frontmatter.parse(contenu)
                self.assertEqual(meta['prisme_type'], t)
                self.assertEqual(meta['prisme_schema'], '1')
                self.assertTrue(meta['prisme_id'])
                self.assertIn('prisme_enregistre_le', meta)
                self.assertEqual(meta['prisme_outil'], 'objets')
                self.assertEqual(meta['prisme_relu'], 'true')
                self.assertNotIn('prisme_valide_du', meta)
                self.assertNotIn('\\', o['chemin'])
                self.assertIn('## ' + types.TYPES[t]['sections'][0], contenu)
        self.assertEqual(len(registre.lister()), 5)
        self.assertEqual(len(registre.lister('prediction')), 1)

    def test_champs_obligatoires(self):
        for t, spec in types.TYPES.items():
            for c in spec['champs']:
                if not c['requis']:
                    continue
                d = EXEMPLES[t].copy(); d.pop(c['nom'])
                with self.subTest(type=t, champ=c['nom']), self.assertRaises(sources.ObjetInvalide):
                    registre.creer(t, 'Objet', d)
        self.assertFalse(registre.lister())

    def test_probabilites_bornees_et_finies(self):
        for v in [-0.1, 1.1, True, False, float('nan'), float('inf'), [], {}, 'abc']:
            with self.subTest(v=v), self.assertRaises(sources.ObjetInvalide):
                types.valider('prediction', 'Objet', dict(EXEMPLES['prediction'], probabilite=v))
        for v in [0, 1, '0.25']:
            titre, d = types.valider('prediction', 'Objet', dict(EXEMPLES['prediction'], probabilite=v))
            self.assertEqual(d['probabilite'], float(v))

    def test_dates_reelles(self):
        for v in ['2026-02-30', '2025-02-29', '20260919', 'demain', '2026-9-19']:
            with self.subTest(v=v), self.assertRaises(sources.ObjetInvalide):
                types.valider('prediction', 'Objet', dict(EXEMPLES['prediction'], echeance=v))
        types.valider('prediction', 'Objet', dict(EXEMPLES['prediction'], echeance='2028-02-29'))

    def test_type_champs_statut_et_injection_yaml_refuses(self):
        essais = [('inconnu', 'X', {}), ('tache', 'X', {'action': 'Faire', 'prisme_id': 'usurpe'}),
                  ('tache', 'X', dict(EXEMPLES['tache'], statut='invente')),
                  ('tache', 'X\nprisme_id: usurpe', EXEMPLES['tache']),
                  ('decision', 'X', dict(EXEMPLES['decision'], choix='oui\nprisme_type: source'))]
        for args in essais:
            with self.subTest(args=args), self.assertRaises(sources.ObjetInvalide):
                types.valider(*args)

    def test_resolution_complete_sans_score(self):
        o = registre.creer('prediction', 'Retour du service', EXEMPLES['prediction'])
        for champs in [dict(o['champs'], statut='resolue'), dict(o['champs'], resultat='oui')]:
            with self.assertRaises(sources.ObjetInvalide):
                registre.modifier(o['cle'], o['titre'], champs)
        champs = dict(o['champs'], statut='resolue', resultat='non', resolu_le='2027-01-03', preuve_resolution='Journal HTTP archivé')
        r = registre.modifier(o['cle'], o['titre'], champs)
        self.assertEqual(r['champs']['resultat'], 'non')
        self.assertNotIn('brier', (VAULT / r['chemin']).read_text())

    def test_modification_preserve_id_notes_libres_et_champs_obsidian(self):
        o = registre.creer('tache', 'Rédiger', EXEMPLES['tache'])
        p = VAULT / o['chemin']
        p.write_text(frontmatter.update(p.read_text(), {'tags': ['travail'], 'personnel': 'à garder'}) + '\nMon paragraphe libre.\n', encoding='utf-8')
        r = registre.modifier(o['cle'], 'Rédiger le guide', dict(o['champs'], statut='terminee'), 'Terminé')
        contenu = p.read_text(encoding='utf-8')
        self.assertEqual(r['id'], o['id'])
        self.assertIn('Mon paragraphe libre.', contenu)
        self.assertEqual(frontmatter.parse(contenu)['personnel'], 'à garder')
        self.assertIn('Statut : terminee', contenu)
        self.assertNotIn('Statut : a_faire', contenu)
        self.assertTrue(list((VAULT / '.trash' / 'versions').rglob('*.md')))

    def test_caracteres_speciaux_relus_sans_deformation(self):
        valeur = 'Chemin "D:\\Documents\\été" et <balise>'
        o = registre.creer('decision', 'Décision "été"', dict(EXEMPLES['decision'], choix=valeur))
        self.assertEqual(o['champs']['choix'], valeur)
        registre.modifier(o['cle'], o['titre'], o['champs'])
        self.assertEqual(registre.lister()[0]['champs']['choix'], valeur)

    def test_doublon_necrase_rien(self):
        o = registre.creer('tache', 'Faire', EXEMPLES['tache'])
        avant = (VAULT / o['chemin']).read_bytes()
        with self.assertRaises(sources.ObjetInvalide):
            registre.creer('tache', ' FAIRE ', dict(EXEMPLES['tache'], action='Autre'))
        self.assertEqual((VAULT / o['chemin']).read_bytes(), avant)

    def test_objet_deplace_reste_visible(self):
        o = registre.creer('entite', 'Centre', EXEMPLES['entite'])
        (VAULT / o['chemin']).rename(VAULT / 'sous' / 'Centre.md')
        self.assertEqual(registre.lister()[0]['chemin'], 'sous/Centre.md')

    def test_retrait_et_rejet_memorise(self):
        o = registre.creer('hypothese', 'Hypothèse', EXEMPLES['hypothese'])
        r = registre.supprimer(o['cle'], 'Réfutée')
        self.assertFalse(registre.lister())
        self.assertTrue(Path(r['corbeille']).is_file())
        self.assertIn('prisme_invalide_le', Path(r['corbeille']).read_text(encoding='utf-8'))
        self.assertIn(o['cle'], file.rejets())
        self.assertIsNone(registre.proposer('hypothese', o['titre'], {}, origine='ia'))


class TestValidation(E11Base):
    def test_agent_incomplet_complete_par_auteur_et_provenance(self):
        h = self.agent()
        r = self.client.post('/api/v1/proposer', headers=h, json={
            'type':'prediction', 'titre':'Prévision Constat', 'champs': {'enonce':'Un événement'}})
        self.assertEqual(r.status_code, 201, r.get_json())
        entree = r.get_json()['entree']
        self.assertFalse(registre.lister())
        invalide = self.post('/api/objets/file/accepter', {'cle':entree['cle']})
        self.assertEqual(invalide.status_code, 400)
        self.assertEqual(len(file.lister()), 1)
        valide = self.post('/api/objets/file/accepter', {'cle':entree['cle'], 'champs':EXEMPLES['prediction'], 'raison':'Je prends ce pari'})
        self.assertEqual(valide.status_code, 200, valide.get_json())
        o = valide.get_json()['objet']
        meta = frontmatter.parse((VAULT / o['chemin']).read_text(encoding='utf-8'))
        self.assertEqual(meta['prisme_origine'], entree['origine'])
        self.assertEqual(meta['prisme_genere_par'], entree['origine'])
        self.assertEqual(meta['prisme_raison'], 'Je prends ce pari')
        self.assertFalse(file.lister())

    def test_agent_ne_peut_pas_sauto_valider_meme_avec_ecriture(self):
        h = self.agent(['lecture', 'proposition', 'ecriture'])
        for t, champs in EXEMPLES.items():
            reglages.enregistrer(t, True, 0)
            r = self.client.post('/api/v1/proposer', headers=h, json={
                'type':t, 'titre':t, 'champs':champs, 'origine':'auteur', 'entree_directe':True, 'relu':True})
            self.assertEqual(r.status_code, 201)
            self.assertNotEqual(r.get_json()['entree']['origine'], 'auteur')
        self.assertFalse(registre.lister())
        for route in ['/api/objets/registre', '/api/objets/file/accepter', '/api/objets/types/reglages']:
            self.assertEqual(self.client.post(route, headers=h, json={}).status_code, 403)

    def test_droits_proposition_et_lecture(self):
        h = self.agent(['lecture'])
        self.assertEqual(self.client.post('/api/v1/proposer', headers=h, json={'type':'tache', 'titre':'Faire'}).status_code, 403)
        self.assertEqual(self.client.get('/api/v1/types', headers=h).status_code, 200)
        self.assertEqual(self.client.get('/api/v1/types').status_code, 401)

    def test_doublon_file_rejet_et_non_conversion_source(self):
        e = registre.proposer('tache', 'Faire', EXEMPLES['tache'], origine='ia')
        self.assertIsNone(registre.proposer('tache', 'FAIRE', {}, origine='ia'))
        with self.assertRaises(sources.ObjetInvalide):
            balayage.accepter(e['cle'])
        file.rejeter(e['cle'], 'Inutile')
        self.assertIsNone(registre.proposer('tache', 'Faire', {}, origine='ia'))
        self.assertEqual(file.raisons_connues()[0]['raison'], 'Inutile')

    def test_doublon_vault_en_file_sans_ecrasement(self):
        o = registre.creer('tache', 'Faire', EXEMPLES['tache'])
        e = registre.proposer('tache', 'Faire', {}, origine='ia')
        self.assertIn('Doublon', e['motif'])
        with self.assertRaises(sources.ObjetInvalide):
            registre.accepter(e['cle'], champs=EXEMPLES['tache'])
        self.assertEqual(registre.lister()[0]['id'], o['id'])
        self.assertTrue(file.par_cle(e['cle']))

    def test_extrait_et_chemins_refuses(self):
        h = self.agent()
        for note, indice, code in [('../hors.md', '', 403), ('Alpha.md', 'inventé', 400)]:
            r = self.client.post('/api/v1/proposer', headers=h, json={'type':'tache', 'titre':'Faire', 'note':note, 'indice':indice})
            self.assertEqual(r.status_code, code, r.get_json())
        self.assertFalse(file.lister())

    def test_lister_api_compatibilite_source_et_filtrage(self):
        h = self.agent()
        registre.creer('tache', 'Faire', EXEMPLES['tache'])
        sources.enregistrer('https://example.org')
        r = self.client.get('/api/v1/objets', headers=h).get_json()
        self.assertEqual(len(r['sources']), 1)
        self.assertEqual(len(r['objets']), 1)
        r = self.client.get('/api/v1/objets?type=tache', headers=h).get_json()
        self.assertEqual(r['sources'], [])
        self.assertEqual(len(r['objets']), 1)
        self.assertEqual(self.client.get('/api/v1/objets?type=faux', headers=h).status_code, 400)

    def test_secondaire_interdit_aux_agents(self):
        secondaire = TMP / 'secondaire-e11'; secondaire.mkdir(exist_ok=True)
        (secondaire / 'secret.md').write_text('secret', encoding='utf-8')
        config.wr_cfg({'workspaces':[str(secondaire)]})
        r = self.client.post('/api/v1/proposer', headers=self.agent(), json={
            'type':'tache', 'titre':'Faire', 'note':str(secondaire / 'secret.md')})
        self.assertEqual(r.status_code, 403)

    def test_json_malforme_refuse(self):
        h = self.agent()
        for route, headers in [('/api/objets/registre', self.h), ('/api/objets/types/reglages', self.h), ('/api/v1/proposer', h)]:
            self.assertEqual(self.client.post(route, headers=headers, json=[1]).status_code, 400)


class TestReglages(E11Base):
    def test_sources_file_si_desactivees_avec_citations_conservees(self):
        for nom in ['Alpha.md', 'sous/Beta.md']:
            (VAULT / nom).write_text('Lien https://example.org/rapport', encoding='utf-8')
        reglages.enregistrer('source', False, 100)
        rapport = balayage.balayer()
        self.assertFalse(rapport['crees'])
        self.assertEqual(len(rapport['deposees']), 1)
        e = rapport['deposees'][0]
        o = balayage.accepter(e['cle'])['objet']
        self.assertEqual(o['cite_par'], ['Alpha.md', 'sous/Beta.md'])
        self.assertTrue(o['relu'])

    def test_source_par_defaut_et_lot_annulable(self):
        (VAULT / 'Alpha.md').write_text('https://example.org/one', encoding='utf-8')
        r = balayage.balayer()
        self.assertEqual(len(r['crees']), 1)
        self.assertFalse(r['crees'][0]['relu'])
        sources.annuler_lot(r['lot'])
        self.assertFalse(sources.lister())

    def test_reglages_invalides_et_persistants(self):
        for actif, seuil in [('false', 90), (True, -1), (True, 101), (True, True), (True, 0.5)]:
            with self.assertRaises(sources.ObjetInvalide):
                reglages.enregistrer('source', actif, seuil)
        reglages.enregistrer('tache', True, 80)
        self.assertEqual(reglages.lire()['tache'], {'entree_directe':True, 'seuil':80})


class TestSymlinks(E11Base):
    def lien(self, cible, lien, dossier=False):
        try:
            lien.symlink_to(cible, target_is_directory=dossier)
        except (OSError, NotImplementedError):
            self.skipTest('Création de liens symboliques indisponible')
        self.addCleanup(lien.unlink, missing_ok=True)

    def test_dossier_objets_hors_vault_refuse(self):
        externe = TMP / 'hors-e11'; externe.mkdir(exist_ok=True)
        self.lien(externe, VAULT / 'Objets', True)
        with self.assertRaises(PermissionError):
            registre.creer('tache', 'Faire', EXEMPLES['tache'])
        self.assertFalse(list(externe.glob('*.md')))

    def test_note_hors_vault_non_lue(self):
        externe = TMP / 'externe-e11.md'
        externe.write_text('---\nprisme_type: tache\nprisme_titre: Secret\n---\n', encoding='utf-8')
        self.lien(externe, VAULT / 'fuite.md')
        self.assertFalse(registre.lister())


if __name__ == '__main__':
    unittest.main()
