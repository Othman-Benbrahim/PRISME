"""Plugin « embeddings-locaux » : recherche semantique sans rien envoyer dehors.

Le vrai modele fait 120 Mo et vient d'Internet : hors de question dans une suite de
tests. On construit a la place un modele ONNX minuscule (tests/fixtures) qui exerce
exactement la meme chaine — tokenisation, inference, moyenne masquee, normalisation,
roles. Ce qui n'est pas verifie ici est dit dans docs/branches/plugin-embeddings.md.
"""
import json
import unittest
from pathlib import Path

from commun import ROOT, TMP, VAULT, reset_vault

from prisme_core import config, plugins
from prisme_core.api import EmbeddingProvider, EmbeddingUnavailable
from prisme_core.app import create_app
from prisme_core.index import fresh_index
from prisme_core.routes import security
from prisme_core.vecteurs import contrat, magasin, recherche, vectorisation

import sys
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import modele_minuscule                                                # noqa: E402

PLUGIN = ROOT / "plugins" / "embeddings-locaux"
DOSSIER_MODELE = Path(TMP) / "modele-minuscule"
SANS_DEPS = not modele_minuscule.disponible()


def _charger_plugin():
    """Charge le plugin comme PRISME le fait, et renvoie son contexte."""
    plugins.load_one(PLUGIN)
    for p in plugins.active_plugins():
        if p.id == "embeddings-locaux":
            return p
    return None


# ── Le contrat, sans dependances ────────────────────────────────────────
class TestPorteDesPlugins(unittest.TestCase):
    """La porte doit exister dans l'API publique, pas seulement dans le coeur."""

    def test_api_expose_le_contrat(self):
        from prisme_core import api
        self.assertIn("EmbeddingProvider", api.__all__)
        self.assertIn("EmbeddingUnavailable", api.__all__)
        self.assertTrue(hasattr(api.PluginContext, "register_embeddings"))

    def test_un_fournisseur_sans_nom_est_refuse(self):
        from prisme_core.api import PluginContext
        ctx = PluginContext("faux", "Faux", PLUGIN, {"id": "faux", "api_version": 1})

        class SansNom(EmbeddingProvider):
            pass

        with self.assertRaises(ValueError):
            ctx.register_embeddings(SansNom)

    def test_role_par_defaut_sans_prefixe(self):
        """Un fournisseur qui n'a pas besoin de roles n'a rien a implementer."""
        class Simple(EmbeddingProvider):
            nom = "simple"

            def __init__(self, cfg):
                self.vus = []

            def vectoriser(self, textes):
                self.vus = list(textes)
                return [[1.0] for _ in textes]

        f = Simple({})
        f.vectoriser_role(["abc"], role="requete")
        self.assertEqual(f.vus, ["abc"], "aucun prefixe ajoute")

    def test_role_applique_le_prefixe(self):
        class Prefixe(EmbeddingProvider):
            nom = "prefixe"

            def __init__(self, cfg):
                self.vus = []

            def prefixe(self, role):
                return "query: " if role == "requete" else "passage: "

            def vectoriser(self, textes):
                self.vus = list(textes)
                return [[1.0] for _ in textes]

        f = Prefixe({})
        f.vectoriser_role(["abc"], role="requete")
        self.assertEqual(f.vus, ["query: abc"])
        f.vectoriser_role(["abc"], role="passage")
        self.assertEqual(f.vus, ["passage: abc"])


# ── Telechargement et validation du modele ──────────────────────────────
class TestModele(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(PLUGIN))
        import modele
        self.modele = modele

    def test_dossier_incomplet_signale_ce_qui_manque(self):
        vide = Path(TMP) / "modele-vide"
        vide.mkdir(exist_ok=True)
        _d, manquants = self.modele.valider_dossier(vide)
        self.assertEqual(sorted(manquants), ["model.onnx", "tokenizer.json"])
        self.assertFalse(self.modele.decrire(vide)["present"])

    def test_dossier_absent(self):
        d, manquants = self.modele.valider_dossier(Path(TMP) / "nexistepas")
        self.assertIsNone(d)
        self.assertTrue(manquants)

    def test_seules_les_url_https_sont_acceptees(self):
        for mauvaise in ("http://exemple.org/m.onnx", "file:///etc/passwd", "ftp://x/y", ""):
            with self.assertRaises(self.modele.ModeleInvalide):
                self.modele._url_sure(mauvaise)
        self.assertTrue(self.modele._url_sure("https://exemple.org/m.onnx"))

    @unittest.skipIf(SANS_DEPS, "onnx absent")
    def test_empreinte_et_description(self):
        modele_minuscule.construire(DOSSIER_MODELE)
        info = self.modele.decrire(DOSSIER_MODELE)
        self.assertTrue(info["present"])
        self.assertEqual(len(info["sha256"]), 64)
        self.assertEqual(info["dimension_annoncee"], modele_minuscule.DIM)
        self.assertEqual(info["sha256"], self.modele.empreinte(DOSSIER_MODELE / "model.onnx"))


# ── Le moteur ───────────────────────────────────────────────────────────
@unittest.skipIf(SANS_DEPS, "onnxruntime, tokenizers ou onnx absent")
class TestMoteur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        modele_minuscule.construire(DOSSIER_MODELE)
        sys.path.insert(0, str(PLUGIN))
        import moteur
        cls.moteur = moteur
        cls.m = moteur.Moteur(DOSSIER_MODELE, prefixes=True)

    @staticmethod
    def cos(a, b):
        return sum(x * y for x, y in zip(a, b))

    def test_vecteurs_normalises(self):
        v, = self.m.encoder(["prediction"], role="passage")
        self.assertAlmostEqual(self.cos(v, v), 1.0, places=4)
        self.assertEqual(len(v), modele_minuscule.DIM)

    def test_meme_theme_plus_proche_que_theme_oppose(self):
        a, b, c = self.m.encoder(["prediction horizon calibrer",
                                  "anticiper echeance prospective",
                                  "oignon huile olive"], role="passage")
        self.assertGreater(self.cos(a, b), self.cos(a, c) + 0.2)

    def test_moyenne_masquee_ne_dilue_pas_les_textes_courts(self):
        """Compter le remplissage ferait s'effondrer la proximite d'un texte court."""
        court, long_ = self.m.encoder(
            ["prediction", "prediction horizon calibrer prospective bascule signal"], role="passage")
        self.assertGreater(self.cos(court, long_), 0.8)

    def test_les_roles_changent_l_encodage(self):
        q, = self.m.encoder(["prediction horizon"], role="requete")
        p, = self.m.encoder(["prediction horizon"], role="passage")
        self.assertLess(self.cos(q, p), 0.9999, "query: et passage: doivent differer")

    def test_prefixes_desactivables(self):
        sans = self.moteur.Moteur(DOSSIER_MODELE, prefixes=False)
        q, = sans.encoder(["prediction horizon"], role="requete")
        p, = sans.encoder(["prediction horizon"], role="passage")
        self.assertAlmostEqual(self.cos(q, p), 1.0, places=4)

    def test_lot_de_longueurs_inegales(self):
        vecteurs = self.m.encoder(["prediction", "oignon huile olive plat cuisine", "horizon"],
                                  role="passage")
        self.assertEqual(len(vecteurs), 3)
        self.assertTrue(all(len(v) == modele_minuscule.DIM for v in vecteurs))

    def test_texte_vide(self):
        v, = self.m.encoder([""], role="passage")
        self.assertEqual(len(v), modele_minuscule.DIM)

    def test_modele_absent(self):
        absent = self.moteur.Moteur(Path(TMP) / "nexistepas")
        with self.assertRaises(self.moteur.MoteurIndisponible):
            absent.encoder(["x"])


# ── Le plugin dans PRISME ───────────────────────────────────────────────
@unittest.skipIf(SANS_DEPS, "onnxruntime, tokenizers ou onnx absent")
class TestPluginIntegre(unittest.TestCase):
    def setUp(self):
        reset_vault()
        magasin.oublier_tout()
        modele_minuscule.construire(DOSSIER_MODELE)
        self.plugin = _charger_plugin()
        self.assertIsNotNone(self.plugin, "le plugin doit se charger")
        self.ctx = self.plugin.ctx
        reglages = self.ctx.data_dir() / "reglages.json"
        reglages.write_text(json.dumps({"dossier": str(DOSSIER_MODELE), "nom": "minuscule",
                                        "prefixes": True, "fils": 0, "empreintes": {}}),
                            encoding="utf-8")
        (VAULT / "Prospective.md").write_text(
            "# Prospective\n\nprediction horizon calibrer prospective bascule\n", encoding="utf-8")
        (VAULT / "Cuisine.md").write_text(
            "# Cuisine\n\noignon huile olive plat cuisine recette\n", encoding="utf-8")
        cfg = config.rd_cfg()
        config.wr_cfg({**{k: cfg[k] for k in ("workspace", "base_url", "model")},
                       "emb_actif": True, "emb_fournisseur": "onnx", "emb_modele": "minuscule",
                       "emb_seuil": recherche.SEUIL_COSINUS})
        self.index = fresh_index()
        magasin.magasin_pour().vider()

    def test_le_fournisseur_est_enregistre_et_local(self):
        self.assertIn("onnx", contrat.noms())
        f = vectorisation.fournisseur_configure()
        self.assertEqual(f.nom, "onnx")
        self.assertFalse(f.distant, "tout l'interet du plugin : rien ne sort")
        ok, raison = f.disponible()
        self.assertTrue(ok, raison)

    def test_vectorisation_puis_recherche_par_le_sens(self):
        r = vectorisation.vectoriser(self.index)
        self.assertTrue(r.get("ok"), r.get("error"))
        self.assertGreater(r["vectorises"], 0)
        res, info = recherche.hybride(self.index, "anticiper echeance")
        self.assertTrue(info["semantique"], info.get("repli"))
        self.assertTrue(res)
        self.assertEqual(res[0]["name"], "Prospective.md")
        self.assertEqual(res[0]["matches"][0]["origine"], "sens")

    def test_signature_contient_le_modele_local(self):
        f = vectorisation.fournisseur_configure()
        self.assertEqual(f.signature(), "onnx:minuscule:%d" % modele_minuscule.DIM)

    def test_modele_absent_declare_indisponible_sans_casser(self):
        reglages = self.ctx.data_dir() / "reglages.json"
        reglages.write_text(json.dumps({"dossier": str(Path(TMP) / "nexistepas"),
                                        "nom": "minuscule", "prefixes": True}), encoding="utf-8")
        f = vectorisation.fournisseur_configure()
        ok, raison = f.disponible()
        self.assertFalse(ok)
        self.assertIn("absent", raison.lower())
        res, info = recherche.hybride(self.index, "oignon")
        self.assertTrue(res, "la recherche par mots continue de marcher")
        self.assertFalse(info["semantique"])


# ── Routes du plugin ────────────────────────────────────────────────────
@unittest.skipIf(SANS_DEPS, "onnxruntime, tokenizers ou onnx absent")
class TestRoutesPlugin(unittest.TestCase):
    def setUp(self):
        reset_vault()
        modele_minuscule.construire(DOSSIER_MODELE)
        _charger_plugin()
        self.c = create_app(with_plugins=False).test_client()
        self.h = {"X-Prisme-Token": security.TOKEN}
        self.post("/api/plugins/embeddings-locaux/reglages",
                  {"dossier": str(DOSSIER_MODELE), "nom": "minuscule"})

    def get(self, url):
        return self.c.get(url, headers=self.h).get_json()

    def post(self, url, data=None):
        return self.c.post(url, headers=self.h, json=data or {})

    def test_etat(self):
        d = self.get("/api/plugins/embeddings-locaux/etat")
        self.assertTrue(d["dependances_ok"], d["dependances"])
        self.assertTrue(d["modele"]["present"])
        self.assertIn("multilingual-e5-small", d["catalogue"])

    def test_essai_donne_un_verdict(self):
        d = self.post("/api/plugins/embeddings-locaux/essai",
                      {"a": "prediction horizon", "b": "anticiper echeance",
                       "c": "oignon huile olive"}).get_json()
        self.assertTrue(d.get("ok"), d.get("error"))
        self.assertGreater(d["proche"], d["lointain"])
        self.assertIn("distingue", d["verdict"])

    def test_epingler_l_empreinte(self):
        d = self.post("/api/plugins/embeddings-locaux/epingler").get_json()
        self.assertTrue(d["ok"])
        self.assertEqual(len(d["sha256"]), 64)

    def test_installer_refuse_un_modele_inconnu(self):
        r = self.post("/api/plugins/embeddings-locaux/installer", {"nom": "inexistant"})
        self.assertEqual(r.status_code, 400)

    def test_reglages_valident_le_nombre_de_fils(self):
        self.assertEqual(self.post("/api/plugins/embeddings-locaux/reglages",
                                   {"fils": "beaucoup"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
