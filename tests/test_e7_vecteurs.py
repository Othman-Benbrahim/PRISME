"""Etape E7 : recherche semantique (docs/decisions/0019)."""
import random
import unittest
from pathlib import Path

from commun import ROOT, VAULT, reset_vault

from prisme_core import config
from prisme_core.app import create_app
from prisme_core.index import fresh_index
from prisme_core.index import search as lexical
from prisme_core.routes import security
from prisme_core.vecteurs import contrat, magasin, quantification as quant, recherche, vectorisation
from prisme_core.vecteurs.contrat import Fournisseur, VecteurIndisponible, enregistrer

# Fournisseur de test : des concepts portes par des dimensions dediees, pour que
# « anticipation » et « prediction » se ressemblent vraiment. Il verifie la plomberie,
# pas la qualite d'un vrai modele.
CONCEPTS = {
    0: ["prediction", "prédiction", "anticipation", "horizon", "calibr", "bascule", "signaux"],
    1: ["cuisine", "oignon", "huile", "olive", "plat"],
    2: ["methode", "méthode", "condition", "refutation", "réfutation"],
}
DIM = 64


@enregistrer
class FournisseurFaux(Fournisseur):
    nom = "faux"
    distant = False
    appels = 0
    en_panne = False

    def __init__(self, cfg):
        self.cfg = cfg or {}

    def modele(self):
        return self.cfg.get("emb_modele") or "faux-v1"

    def dimension(self):
        return DIM

    def disponible(self):
        return (False, "Fournisseur simulé en panne") if FournisseurFaux.en_panne else (True, "")

    def vectoriser(self, textes):
        if FournisseurFaux.en_panne:
            raise VecteurIndisponible("Fournisseur simulé en panne")
        FournisseurFaux.appels += 1
        out = []
        for t in textes:
            bas = (t or "").lower()
            v = [0.0] * DIM
            for dim, mots in CONCEPTS.items():
                for m in mots:
                    if m in bas:
                        v[dim] += 1.0
            random.seed(abs(hash(bas)) % 10**6)
            for i in range(10, DIM):
                v[i] = random.gauss(0, 0.05)
            out.append(v)
        return out


class VecteursBase(unittest.TestCase):
    def setUp(self):
        reset_vault()
        magasin.oublier_tout()
        FournisseurFaux.appels = 0
        FournisseurFaux.en_panne = False
        (VAULT / "Methode.md").write_text(
            "# Méthode\n\nLa prédiction calibrée demande un horizon et une condition de réfutation.\n",
            encoding="utf-8")
        (VAULT / "Cuisine.md").write_text(
            "# Cuisine\n\nFaire revenir les oignons dans l'huile d'olive.\n", encoding="utf-8")
        cfg = config.rd_cfg()
        config.wr_cfg({**{k: cfg[k] for k in ("workspace", "base_url", "model")},
                       "emb_actif": True, "emb_fournisseur": "faux", "emb_modele": "faux-v1",
                       "emb_api_key": "",
                       # le seuil est un reglage persistant : un test qui le change ne doit
                       # pas contaminer les suivants
                       "emb_seuil": recherche.SEUIL_COSINUS})
        self.index = fresh_index()
        magasin.magasin_pour().vider()

    def vectoriser(self):
        return vectorisation.vectoriser(self.index)


# ── Quantification ──────────────────────────────────────────────────────
class TestQuantification(unittest.TestCase):
    def test_binarisation_et_hamming(self):
        a = quant.binariser([1.0, -1.0, 1.0, -1.0])
        b = quant.binariser([1.0, -1.0, 1.0, 1.0])
        self.assertEqual((a ^ a).bit_count(), 0)
        self.assertEqual((a ^ b).bit_count(), 1, "un seul signe differe")

    def test_normalisation(self):
        v = quant.normaliser([3.0, 4.0])
        self.assertAlmostEqual(quant.produit(v, v), 1.0, places=5)
        self.assertEqual(list(quant.normaliser([0.0, 0.0])), [0.0, 0.0], "pas de division par zero")

    def test_aller_retour_octets(self):
        v = [0.5, -0.25, 0.125]
        self.assertEqual([round(x, 3) for x in quant.depuis_octets(quant.vers_octets(v))], v)

    def test_preselection_ramene_le_plus_proche(self):
        cible = quant.binariser([1.0] * 32)
        loin = quant.binariser([-1.0] * 32)
        ordre = quant.preselectionner(cible, [("loin", loin), ("proche", cible)], combien=2)
        self.assertEqual(ordre[0], "proche")

    def test_rrf_recompense_l_accord(self):
        """Un element trouve par les deux recherches passe devant un premier d'une seule.

        C'est tout l'interet du RRF : il ne compare pas un BM25 a un cosinus — ils ne
        sont pas commensurables — il ne compare que des rangs, et recompense l'accord.
        """
        fusion = dict(quant.fusionner(["a", "b"], ["c", "b"]))
        self.assertGreater(fusion["b"], fusion["a"], "b est dans les deux listes")
        self.assertGreater(fusion["b"], fusion["c"])
        self.assertAlmostEqual(fusion["a"], fusion["c"], places=9, msg="memes rangs, memes scores")

    def test_diversification(self):
        elements = [("x", "f1"), ("y", "f1"), ("z", "f1"), ("w", "f2")]
        garde = quant.diversifier(elements, lambda e: e[1], par_groupe=2, total=10)
        self.assertEqual(len(garde), 3, "deux par fichier au plus")


# ── Magasin ─────────────────────────────────────────────────────────────
class TestMagasin(VecteursBase):
    def test_vecteurs_survivent_a_la_reconstruction_de_l_index(self):
        """Le magasin est indexe par empreinte de segment, pas par identifiant d'index."""
        self.vectoriser()
        avant = magasin.magasin_pour().compte()
        self.assertGreater(avant, 0)
        self.index.rebuild()
        appels = FournisseurFaux.appels
        self.vectoriser()
        self.assertEqual(magasin.magasin_pour().compte(), avant)
        self.assertEqual(FournisseurFaux.appels, appels, "rien n'est revectorise")

    def test_changer_de_modele_vide_le_magasin(self):
        self.vectoriser()
        self.assertGreater(magasin.magasin_pour().compte(), 0)
        cfg = config.rd_cfg()
        config.wr_cfg({**cfg, "emb_modele": "faux-v2"})
        r = self.vectoriser()
        self.assertTrue(r["revectorisation"], "un index ne melange jamais deux modeles (0019)")
        self.assertEqual(magasin.magasin_pour().signature(), "faux:faux-v2:%d" % DIM)

    def test_segments_disparus_sont_oublies(self):
        self.vectoriser()
        avant = magasin.magasin_pour().compte()
        (VAULT / "Cuisine.md").unlink()
        self.index.rebuild()
        r = self.vectoriser()
        self.assertGreater(r["oublies"], 0)
        self.assertLess(magasin.magasin_pour().compte(), avant)

    def test_seuls_les_nouveaux_segments_sont_envoyes(self):
        self.vectoriser()
        appels = FournisseurFaux.appels
        (VAULT / "Neuve.md").write_text("# Neuve\n\nUn horizon de prédiction.\n", encoding="utf-8")
        self.index.rebuild()
        self.vectoriser()
        self.assertEqual(FournisseurFaux.appels, appels + 1, "un seul lot pour la note neuve")


# ── Recherche ───────────────────────────────────────────────────────────
class TestRecherche(VecteursBase):
    def test_le_sens_trouve_ce_que_les_mots_ratent(self):
        self.vectoriser()
        self.assertEqual(lexical.search(self.index, "anticipation"), [],
                         "le mot n'apparait nulle part")
        res, info = recherche.hybride(self.index, "anticipation")
        self.assertTrue(res)
        self.assertEqual(info["mode"], "hybride")
        self.assertIn("Methode.md", [r["name"] for r in res])
        self.assertEqual(res[0]["matches"][0]["origine"], "sens")

    def test_le_hors_sujet_ne_remonte_pas(self):
        """Sans plancher, la recherche par le sens rendrait toujours le moins mauvais."""
        self.vectoriser()
        res, _info = recherche.hybride(self.index, "zèbre")
        self.assertEqual(res, [])

    def test_une_correspondance_exacte_est_marquee_les_deux(self):
        self.vectoriser()
        res, _info = recherche.hybride(self.index, "oignons")
        self.assertEqual(res[0]["name"], "Cuisine.md")
        self.assertEqual(res[0]["matches"][0]["origine"], "les deux")

    def test_repli_quand_le_fournisseur_tombe(self):
        self.vectoriser()
        FournisseurFaux.en_panne = True
        res, info = recherche.hybride(self.index, "oignons")
        self.assertTrue(res, "la recherche ne tombe jamais")
        self.assertFalse(info["semantique"])
        self.assertIn("panne", info["repli"])

    def test_repli_quand_rien_n_est_vectorise(self):
        res, info = recherche.hybride(self.index, "oignons")
        self.assertTrue(res)
        self.assertEqual(info["mode"], "lexical")
        self.assertIn("vectorisation", info["repli"].lower())

    def test_signature_incoherente_refusee(self):
        self.vectoriser()
        cfg = config.rd_cfg()
        config.wr_cfg({**cfg, "emb_modele": "autre"})
        with self.assertRaises(VecteurIndisponible):
            recherche.semantique("prédiction")

    def test_desactivee_par_defaut(self):
        cfg = config.rd_cfg()
        config.wr_cfg({**cfg, "emb_actif": False})
        self.assertIsNone(vectorisation.fournisseur_configure())
        res, info = recherche.hybride(self.index, "oignons")
        self.assertTrue(res)
        self.assertFalse(info["semantique"])


# ── Contrat ─────────────────────────────────────────────────────────────
class TestContrat(VecteursBase):
    def test_signature(self):
        f = contrat.construire("faux", config.rd_cfg())
        self.assertEqual(f.signature(), "faux:faux-v1:%d" % DIM)

    def test_fournisseur_inconnu(self):
        with self.assertRaises(VecteurIndisponible):
            contrat.construire("inexistant", {})

    def test_fournisseurs_du_coeur_enregistres(self):
        for attendu in ("api", "ollama"):
            self.assertIn(attendu, contrat.noms())

    def test_lots(self):
        lots = list(contrat.par_lots(["a"] * 150, taille=64))
        self.assertEqual([len(x) for x in lots], [64, 64, 22])

    def test_texte_tronque(self):
        lot = next(contrat.par_lots(["x" * 20000]))
        self.assertEqual(len(lot[0]), contrat.MAX_CAR)


# ── Routes ──────────────────────────────────────────────────────────────
class TestRoutes(VecteursBase):
    def setUp(self):
        super().setUp()
        self.c = create_app(with_plugins=False).test_client()
        self.h = {"X-Prisme-Token": security.TOKEN}

    def get(self, url):
        return self.c.get(url, headers=self.h).get_json()

    def post(self, url, data=None):
        return self.c.post(url, headers=self.h, json=data or {})

    def test_etat(self):
        d = self.get("/api/vecteurs/etat")
        self.assertTrue(d["actif"])
        self.assertTrue(d["disponible"])
        self.assertFalse(d["distant"])
        self.assertIn("faux", d["fournisseurs"])

    def test_vectoriser_puis_chercher(self):
        r = self.post("/api/vecteurs/vectoriser").get_json()
        self.assertTrue(r["ok"])
        d = self.get("/api/search?q=anticipation")
        self.assertTrue(d["results"])
        self.assertTrue(d["recherche"]["semantique"])

    def test_mode_lexical_force(self):
        self.post("/api/vecteurs/vectoriser")
        d = self.get("/api/search?q=anticipation&mode=lexical")
        self.assertEqual(d["results"], [])
        self.assertFalse(d["recherche"]["semantique"])

    def test_tester(self):
        d = self.post("/api/vecteurs/tester", {"emb_fournisseur": "faux"}).get_json()
        self.assertTrue(d["ok"])
        self.assertEqual(d["dimension"], DIM)

    def test_config_valide_le_fournisseur(self):
        self.assertEqual(self.post("/api/vecteurs/config",
                                   {"emb_fournisseur": "inexistant"}).status_code, 400)
        self.assertEqual(self.post("/api/vecteurs/config", {"emb_seuil": "abc"}).status_code, 400)
        d = self.post("/api/vecteurs/config", {"emb_seuil": 5}).get_json()
        self.assertLessEqual(float(config.rd_cfg()["emb_seuil"]), 0.95, "seuil borne")

    def test_cle_embeddings_separee_du_chat(self):
        self.post("/api/vecteurs/config", {"emb_api_key": "secret-emb"})
        cfg = config.rd_cfg()
        self.assertEqual(cfg["emb_api_key"], "secret-emb")
        self.assertNotEqual(cfg["api_key"], "secret-emb", "le chat garde sa propre cle")
        brut = (ROOT / "tests").parent  # la cle stockee ne doit pas etre en clair si DPAPI existe
        self.assertIn(cfg["emb_key_state"], ("clair", "chiffree"))

    def test_vider(self):
        self.post("/api/vecteurs/vectoriser")
        self.assertGreater(magasin.magasin_pour().compte(), 0)
        d = self.post("/api/vecteurs/vider").get_json()
        self.assertGreater(d["supprimes"], 0)
        self.assertEqual(magasin.magasin_pour().compte(), 0)


# ── Interface ───────────────────────────────────────────────────────────
class TestInterface(unittest.TestCase):
    def setUp(self):
        self.web = ROOT / "prisme_core" / "web"
        self.html = (self.web / "index.html").read_text(encoding="utf-8")

    def test_page_cablee(self):
        for attendu in ('src="/static/js/vecteurs.js"', 'href="/static/css/vecteurs.css"',
                        'id="vec-actif"', 'id="vec-etat"', 'id="sr-mode"'):
            self.assertIn(attendu, self.html, attendu)

    def test_aucun_popup_du_navigateur(self):
        js = (self.web / "js" / "vecteurs.js").read_text(encoding="utf-8")
        propre = js.replace("confirmer(", "").replace("demanderTexte(", "")
        for interdit in ("alert(", "confirm(", "prompt("):
            self.assertNotIn(interdit, propre)

    def test_le_mode_distant_est_annonce(self):
        """0019 : le mode actif est toujours visible, et l'envoi distant explicite."""
        js = (self.web / "js" / "vecteurs.js").read_text(encoding="utf-8")
        self.assertIn("MODE DISTANT", js)
        self.assertIn("rien ne sort de votre machine", js.lower())


if __name__ == "__main__":
    unittest.main()
