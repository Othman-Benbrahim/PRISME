"""Etape E5 : file de validation, entree directe des imports en masse, objet Source."""
import json
import unittest
from pathlib import Path

from commun import ROOT, TMP, VAULT, reset_vault

from prisme_core import frontmatter, objets
from prisme_core.app import create_app
from prisme_core.objets import balayage, detection, sources
from prisme_core.objets import file as filedattente
from prisme_core.routes import security


class ObjetsBase(unittest.TestCase):
    def setUp(self):
        reset_vault()
        filedattente.vider()
        for cle in list(filedattente.rejets()):
            filedattente.oublier_rejet(cle)
        from prisme_core.engram import ingestion
        ingestion.ecrire_registre({})
        (VAULT / "Veille.md").write_text(
            "# Veille\n\n"
            "Lu https://www.exemple.org/Etude/2026?utm_source=news&id=7 ce matin.\n"
            "Voir aussi arXiv:2401.09876v3 et le DOI 10.1000/xyz123.\n"
            "Le rapport Kybernetica sur la prospective dit la meme chose.\n",
            encoding="utf-8")
        (VAULT / "sous" / "Notes.md").write_text(
            "# Notes\n\nMeme page : https://exemple.org/Etude/2026/?id=7 ; "
            "et https://arxiv.org/abs/2401.09876 pour l'article.\n",
            encoding="utf-8")


# ── Reperage mecanique ──────────────────────────────────────────────────
class TestDetection(unittest.TestCase):
    def test_url_normalisee(self):
        a = detection.normaliser_url("http://www.Exemple.org/Page/?utm_source=x&b=2&a=1")
        b = detection.normaliser_url("https://exemple.org/Page?a=1&b=2")
        self.assertEqual(a, b, "protocole, www et parametres de suivi ne font pas deux sources")
        self.assertEqual(a, "https://exemple.org/Page?a=1&b=2")

    def test_url_invalide(self):
        for mauvaise in ("http://localhost:5000/x", "https://machine/interne", "pas une url"):
            self.assertIsNone(detection.normaliser_url(mauvaise))

    def test_arxiv_sans_version(self):
        self.assertEqual(detection.normaliser_arxiv("2401.09876v3"), "arxiv:2401.09876")

    def test_identifiant_prime_sur_l_adresse(self):
        """Une page arXiv et l'identifiant nu designent le meme travail."""
        refs = detection.references("arXiv:2401.09876 puis https://arxiv.org/abs/2401.09876v2")
        self.assertEqual([r["cle"] for r in refs], ["arxiv:2401.09876"])

    def test_doi_dans_une_url_doi_org(self):
        refs = detection.references("https://doi.org/10.1000/xyz123 et 10.1000/xyz123")
        self.assertEqual([r["cle"] for r in refs], ["doi:10.1000/xyz123"])

    def test_isbn(self):
        refs = detection.references("ISBN 978-2-07-036822-8")
        self.assertEqual(refs[0]["cle"], "isbn:9782070368228")
        self.assertEqual(refs[0]["genre"], "isbn")

    def test_ponctuation_de_phrase_exclue(self):
        refs = detection.references("Voir https://exemple.org/page.")
        self.assertEqual(refs[0]["cle"], "https://exemple.org/page")

    def test_texte_sans_reference(self):
        self.assertEqual(detection.references("Aucune source ici, juste du texte."), [])


# ── Entree directe ──────────────────────────────────────────────────────
class TestBalayage(ObjetsBase):
    def test_entree_directe_non_relue(self):
        r = balayage.balayer()
        self.assertEqual(r["references"], 3, "une URL, un arXiv, un DOI")
        liste = sources.lister()
        self.assertEqual(len(liste), 3)
        self.assertTrue(all(not o["relu"] for o in liste), "entree directe = non relu (0021)")
        self.assertTrue(all(o["lot"] == r["lot"] for o in liste))
        self.assertTrue(all(o["statut"] == "citee" for o in liste))

    def test_dedoublonnage_entre_notes(self):
        balayage.balayer()
        url = sources.par_cle("https://exemple.org/Etude/2026?id=7")
        self.assertIsNotNone(url, "la meme page citee deux fois ne fait qu'un objet")
        self.assertEqual(sorted(url["cite_par"]), ["Veille.md", "sous/Notes.md"])

    def test_chemins_toujours_en_barres_obliques(self):
        """Garde-fou Windows : `relative_to` y rend « sous\\Notes.md ».

        Ces chemins finissent dans `prisme_cite_par` et dans les liens [[…]] : un
        antislash rendrait le vault illisible apres un passage d'une machine a l'autre.
        Ce test echoue sous Windows si la normalisation saute.
        """
        balayage.balayer()
        for obj in sources.lister():
            for c in obj["cite_par"]:
                self.assertNotIn("\\", c, obj["reference"])
        url = sources.par_cle("https://exemple.org/Etude/2026?id=7")
        self.assertIn("sous/Notes.md", url["cite_par"])

    def test_objet_est_une_note_du_vault(self):
        balayage.balayer()
        obj = sources.par_cle("arxiv:2401.09876")
        p = Path(obj["chemin"])
        self.assertTrue(p.is_file())
        self.assertTrue(str(p).startswith(str(VAULT / "Objets" / "Sources")))
        meta = frontmatter.parse(p.read_text(encoding="utf-8"))
        self.assertEqual(meta["prisme_type"], "source")
        self.assertEqual(meta["prisme_reference"], "arxiv:2401.09876")
        self.assertIn("## Citée dans", p.read_text(encoding="utf-8"))

    def test_second_balayage_idempotent(self):
        balayage.balayer()
        avant = {o["chemin"] for o in sources.lister()}
        r2 = balayage.balayer()
        self.assertEqual(r2["crees"], [], "rien de neuf a creer")
        self.assertEqual({o["chemin"] for o in sources.lister()}, avant)

    def test_le_corps_ecrit_a_la_main_est_respecte(self):
        balayage.balayer()
        p = Path(sources.par_cle("doi:10.1000/xyz123")["chemin"])
        texte = p.read_text(encoding="utf-8")
        p.write_text(texte.replace("## Citée dans", "## Mes notes\n\nÀ relire.\n\n## Citée dans"),
                     encoding="utf-8")
        (VAULT / "Autre.md").write_text("# Autre\n\n10.1000/xyz123\n", encoding="utf-8")
        balayage.balayer()
        final = p.read_text(encoding="utf-8")
        self.assertIn("À relire.", final, "PRISME ne reecrit que la section des citations")
        self.assertIn("[[Autre]]", final)

    def test_lot_annulable_sauf_les_relus(self):
        r = balayage.balayer()
        sources.marquer_relu("arxiv:2401.09876", True)
        bilan = sources.annuler_lot(r["lot"])
        self.assertEqual(len(bilan["conserves"]), 1)
        restants = sources.lister()
        self.assertEqual([o["reference"] for o in restants], ["arxiv:2401.09876"])

    def test_un_rejet_memorise_ne_revient_pas(self):
        balayage.balayer()
        sources.supprimer("doi:10.1000/xyz123", raison="hors sujet")
        r = balayage.balayer()
        self.assertIn("doi:10.1000/xyz123", r["ignores"])
        self.assertIsNone(sources.par_cle("doi:10.1000/xyz123"))
        self.assertEqual(filedattente.rejets()["doi:10.1000/xyz123"]["raison"], "hors sujet")

    def test_objets_lies_a_une_note(self):
        balayage.balayer()
        liste = balayage.objets_lies_a("Veille.md")
        self.assertEqual(len(liste), 3)
        self.assertTrue(all(o["non_relu"] for o in liste), "marqueur des objets non relus (0021)")


# ── Statut depuis ENGRAM ────────────────────────────────────────────────
class TestStatutEngram(ObjetsBase):
    def test_source_ingeree_quand_engram_l_a_importee(self):
        from prisme_core.engram import ingestion
        note = VAULT / "Sources" / "etude.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("# Etude\n", encoding="utf-8")
        ingestion.ecrire_registre({"abc": {
            "chemin": "https://exemple.org/Etude/2026?id=7", "titre": "Etude 2026",
            "notes": [str(note)], "importee_le": "2026-09-18T10:00:00"}})
        balayage.balayer()
        obj = sources.par_cle("https://exemple.org/Etude/2026?id=7")
        self.assertEqual(obj["statut"], "ingeree")
        self.assertEqual(obj["note_liee"], str(note))
        autre = sources.par_cle("arxiv:2401.09876")
        self.assertEqual(autre["statut"], "citee", "ce qu'ENGRAM ignore reste « citee »")

    def test_rafraichir_apres_coup(self):
        balayage.balayer()
        self.assertEqual(sources.par_cle("arxiv:2401.09876")["statut"], "citee")
        from prisme_core.engram import ingestion
        note = VAULT / "Sources" / "papier.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("# Papier\n", encoding="utf-8")
        ingestion.ecrire_registre({"d1": {"chemin": "/tmp/arXiv 2401.09876.pdf", "titre": "",
                                          "notes": [str(note)]}})
        self.assertEqual(sources.rafraichir_statuts(), 1)
        self.assertEqual(sources.par_cle("arxiv:2401.09876")["statut"], "ingeree")


# ── File de validation ──────────────────────────────────────────────────
class TestFile(ObjetsBase):
    def entree(self, cle="texte:rapport kybernetica", **kw):
        base = {"cle": cle, "titre": "Rapport Kybernetica", "genre": "texte",
                "origine": "ia", "note": "Veille.md",
                "indice": "Le rapport Kybernetica sur la prospective"}
        base.update(kw)
        return filedattente.ajouter(base)

    def test_depot_et_doublon(self):
        self.assertIsNotNone(self.entree())
        self.assertIsNone(self.entree(), "deja en file")
        self.assertEqual(len(filedattente.lister()), 1)

    def test_rejet_memorise_bloque_le_redepot(self):
        self.entree()
        filedattente.rejeter("texte:rapport kybernetica", "pas une source, une opinion")
        self.assertEqual(filedattente.lister(), [])
        self.assertIsNone(self.entree(), "un refus memorise ne revient pas")
        self.assertEqual(filedattente.raisons_connues()[0]["raison"], "pas une source, une opinion")

    def test_oublier_un_rejet_rouvre_la_porte(self):
        self.entree()
        filedattente.rejeter("texte:rapport kybernetica", "non")
        filedattente.oublier_rejet("texte:rapport kybernetica")
        self.assertIsNotNone(self.entree())

    def test_plafond_par_origine(self):
        for i in range(filedattente.PLAFOND_PAR_ORIGINE):
            filedattente.ajouter({"cle": "texte:t%d" % i, "origine": "ia"})
        self.assertIsNone(filedattente.ajouter({"cle": "texte:trop", "origine": "ia"}))
        self.assertIsNotNone(filedattente.ajouter({"cle": "texte:autre", "origine": "agent"}))

    def test_accepter_cree_l_objet(self):
        self.entree()
        r = balayage.accepter("texte:rapport kybernetica", raison="source solide")
        self.assertTrue(r["objet"]["relu"], "ce que tu valides est relu par definition")
        self.assertEqual(r["objet"]["cite_par"], ["Veille.md"])
        self.assertEqual(filedattente.lister(), [])

    def test_accepter_en_corrigeant_la_reference(self):
        self.entree()
        r = balayage.accepter("texte:rapport kybernetica",
                              titre="Kybernetica 2026", reference="https://kybernetica.example/rapport")
        self.assertEqual(r["objet"]["reference"], "https://kybernetica.example/rapport")
        self.assertEqual(r["objet"]["genre"], "url")
        self.assertEqual(r["objet"]["titre"], "Kybernetica 2026")

    def test_reference_corrigee_invalide_refusee(self):
        self.entree()
        with self.assertRaises(objets.ObjetInvalide):
            balayage.accepter("texte:rapport kybernetica", reference="ceci n'est pas une reference")

    def test_ia_ecarte_ce_qui_n_est_pas_dans_la_note(self):
        """Garde-fou : une proposition sans extrait litteral retrouve est une invention."""
        appels = []

        def faux_appel(cfg, msgs, **kw):
            appels.append(msgs)
            return (json.dumps([
                {"titre": "Rapport Kybernetica", "indice": "Le rapport Kybernetica sur la prospective",
                 "motif": "cite en clair"},
                {"titre": "Etude fantome", "indice": "une phrase qui n'existe nulle part", "motif": "?"},
            ]), None)

        original = balayage._ai_call
        balayage._ai_call = faux_appel
        try:
            r = balayage.proposer_par_ia(limite=2)
        finally:
            balayage._ai_call = original
        self.assertTrue(appels, "le modele a bien ete appele")
        self.assertEqual(len(r["deposees"]), 1)
        self.assertEqual(r["ecartees"], 1)
        self.assertEqual(r["deposees"][0]["titre"], "Rapport Kybernetica")

    def test_json_du_modele_tolere_les_balises(self):
        self.assertEqual(balayage._json_du_modele('```json\n[{"titre":"A"}]\n```'), [{"titre": "A"}])
        self.assertEqual(balayage._json_du_modele("Voici : [] merci"), [])
        self.assertEqual(balayage._json_du_modele("pas de json"), [])


# ── Fusion ──────────────────────────────────────────────────────────────
class TestFusion(ObjetsBase):
    def test_fusion_puis_annulation(self):
        balayage.balayer()
        garde, absorbe = "arxiv:2401.09876", "doi:10.1000/xyz123"
        r = balayage.fusionner(garde, absorbe, raison="meme article")
        self.assertIsNone(sources.par_cle(absorbe) and sources.par_cle(absorbe)["reference"] == absorbe
                          or None)
        obj = sources.par_cle(garde)
        self.assertIn(absorbe, obj["alias"], "la cle absorbee reste retrouvable")
        self.assertEqual(sources.par_cle(absorbe)["reference"], garde, "l'alias mene a l'objet garde")
        meta = frontmatter.parse(Path(obj["chemin"]).read_text(encoding="utf-8"))
        self.assertTrue(any("meme article" in str(j) for j in meta["prisme_fusions"]),
                        "le journal des fusions garde la raison")
        balayage.defusionner(garde, absorbe)
        self.assertNotIn(absorbe, sources.par_cle(garde)["alias"])
        self.assertEqual(sources.par_cle(absorbe)["reference"], absorbe)

    def test_fusion_d_une_proposition_en_file(self):
        balayage.balayer()
        filedattente.ajouter({"cle": "texte:le meme papier", "titre": "Le meme papier",
                              "origine": "ia", "note": "Veille.md"})
        balayage.fusionner("arxiv:2401.09876", "texte:le meme papier")
        self.assertEqual(filedattente.lister(), [], "la proposition sort de la file")
        self.assertIn("texte:le meme papier", sources.par_cle("arxiv:2401.09876")["alias"])

    def test_fusion_sur_soi_meme_refusee(self):
        balayage.balayer()
        with self.assertRaises(objets.ObjetInvalide):
            balayage.fusionner("arxiv:2401.09876", "arxiv:2401.09876")


# ── Routes ──────────────────────────────────────────────────────────────
class TestRoutes(ObjetsBase):
    def setUp(self):
        super().setUp()
        self.c = create_app(with_plugins=False).test_client()
        self.h = {"X-Prisme-Token": security.TOKEN}

    def post(self, url, data=None):
        return self.c.post(url, headers=self.h, json=data or {})

    def get(self, url):
        return self.c.get(url, headers=self.h).get_json()

    def test_parcours_complet(self):
        r = self.post("/api/objets/balayer").get_json()
        self.assertEqual(r["references"], 3)
        d = self.get("/api/objets/sources")
        self.assertEqual(len(d["sources"]), 3)
        self.assertEqual(d["lots"][0]["non_relus"], 3)
        self.assertEqual(len(self.get("/api/objets/sources?relu=false")["sources"]), 3)
        self.assertEqual(self.get("/api/objets/sources?relu=true")["sources"], [])
        self.post("/api/objets/relu", {"cle": "arxiv:2401.09876", "relu": True})
        self.assertEqual(len(self.get("/api/objets/sources?relu=true")["sources"]), 1)
        bilan = self.post("/api/objets/lot/annuler", {"lot": r["lot"]}).get_json()
        self.assertEqual(len(bilan["conserves"]), 1)

    def test_route_file_et_rejets(self):
        filedattente.ajouter({"cle": "texte:a", "titre": "A", "origine": "ia", "note": "Veille.md"})
        self.assertEqual(len(self.get("/api/objets/file")["entrees"]), 1)
        self.assertEqual(self.post("/api/objets/file/rejeter",
                                   {"cle": "texte:a", "raison": "non"}).status_code, 200)
        self.assertIn("texte:a", self.get("/api/objets/file")["rejets"])
        self.assertEqual(self.post("/api/objets/rejets/oublier", {"cle": "texte:a"}).status_code, 200)
        self.assertEqual(self.get("/api/objets/file")["rejets"], {})

    def test_route_note(self):
        self.post("/api/objets/balayer")
        d = self.get("/api/objets/note?path=Veille.md")
        self.assertEqual(len(d["objets"]), 3)
        self.assertTrue(d["objets"][0]["non_relu"])

    def test_erreurs(self):
        self.assertEqual(self.post("/api/objets/relu", {"cle": "inconnue"}).status_code, 404)
        self.assertEqual(self.post("/api/objets/lot/annuler", {"lot": ""}).status_code, 400)
        self.assertEqual(self.post("/api/objets/file/accepter", {"cle": "absente"}).status_code, 400)
        self.assertEqual(self.post("/api/objets/rejets/oublier", {"cle": "absente"}).status_code, 404)
        self.assertEqual(self.post("/api/objets/balayer", {"dossier": str(TMP)}).status_code, 403)

    def test_ia_sans_cle(self):
        from prisme_core import config
        cfg = config.rd_cfg()
        config.wr_cfg({**cfg, "base_url": "https://api.exemple.com/v1", "api_key": ""})
        try:
            self.assertEqual(self.post("/api/objets/ia").status_code, 400)
        finally:
            config.wr_cfg(cfg)


# ── Interface ───────────────────────────────────────────────────────────
class TestInterface(unittest.TestCase):
    def setUp(self):
        self.html = (ROOT / "prisme_core" / "web" / "index.html").read_text(encoding="utf-8")

    def test_page_cablee(self):
        for attendu in ('src="/static/js/objets.js"', 'href="/static/css/objets.css"',
                        'id="mobjets"', 'onclick="openObjets()"', 'id="ed-objets"'):
            self.assertIn(attendu, self.html, attendu)

    def test_aucun_popup_du_navigateur(self):
        js = (ROOT / "prisme_core" / "web" / "js" / "objets.js").read_text(encoding="utf-8")
        for interdit in ("alert(", "confirm(", "prompt("):
            self.assertNotIn(interdit, js.replace("confirmer(", "").replace("demanderTexte(", ""),
                             "les dialogues passent par l'interface")

    def test_ordre_des_scripts(self):
        """objets.js a besoin de dialogues.js et de tabs.js : il vient apres."""
        for avant in ("dialogues.js", "tabs.js", "engram.js"):
            self.assertLess(self.html.index(avant), self.html.index("objets.js"), avant)


if __name__ == "__main__":
    unittest.main()
