"""Etape E12 : plusieurs racines de vault (docs/decisions/0028).

L'enjeu de cette etape n'est pas le confort, c'est `safe_path` : la garde qui empeche
une page, un plugin ou un agent de lire le reste du disque. Elle est elargie a une
liste, pas levee. La majorite des tests ci-dessous verifient ce qui reste refuse.
"""
import unittest
from pathlib import Path

from commun import ROOT, TMP, VAULT, reset_vault

from prisme_core import config, vault
from prisme_core.agents import cles
from prisme_core.app import create_app
from prisme_core.index import fresh_index, get_index
from prisme_core.routes import security

SECONDE = Path(TMP) / "vault-second"
DEHORS = Path(TMP) / "dehors"


class RacinesBase(unittest.TestCase):
    def setUp(self):
        reset_vault()
        SECONDE.mkdir(parents=True, exist_ok=True)
        DEHORS.mkdir(parents=True, exist_ok=True)
        for f in SECONDE.glob("*.md"):
            f.unlink()
        (SECONDE / "Second.md").write_text("# Second\n\nune note du second vault, mot-rare-second\n",
                                           encoding="utf-8")
        (DEHORS / "Prive.md").write_text("# Privé\n\nsecret\n", encoding="utf-8")
        cfg = config.rd_cfg()
        config.wr_cfg({**{k: cfg[k] for k in ("workspace", "base_url", "model")},
                       "workspaces": [], "emb_actif": False})
        self.c = create_app(with_plugins=False).test_client()
        self.h = {"X-Prisme-Token": security.TOKEN}

    def declarer(self):
        config.wr_cfg({"workspaces": [str(SECONDE)]})

    def get(self, url, **kw):
        return self.c.get(url, headers=self.h, **kw).get_json()

    def post(self, url, data=None):
        return self.c.post(url, headers=self.h, json=data or {})


# ── La garde ────────────────────────────────────────────────────────────
class TestGarde(RacinesBase):
    def test_une_seule_racine_par_defaut(self):
        self.assertEqual(vault.vault_roots(), [VAULT.resolve()])

    def test_hors_racines_toujours_refuse(self):
        self.declarer()
        with self.assertRaises(PermissionError):
            vault.safe_path(str(DEHORS / "Prive.md"))
        with self.assertRaises(PermissionError):
            vault.safe_path("/etc/passwd")

    def test_la_seconde_racine_devient_accessible(self):
        with self.assertRaises(PermissionError):
            vault.safe_path(str(SECONDE / "Second.md"))
        self.declarer()
        self.assertEqual(vault.safe_path(str(SECONDE / "Second.md")), SECONDE / "Second.md")

    def test_chemin_relatif_vise_la_principale(self):
        self.declarer()
        self.assertEqual(vault.safe_path("Alpha.md"), VAULT.resolve() / "Alpha.md")

    def test_racine_imbriquee_ecartee(self):
        """Deux racines imbriquees feraient appartenir un meme fichier a deux index."""
        config.wr_cfg({"workspaces": [str(VAULT / "sous")]})
        self.assertEqual(vault.vault_roots(), [VAULT.resolve()])

    def test_doublons_ecartes(self):
        config.wr_cfg({"workspaces": [str(SECONDE), str(SECONDE)]})
        self.assertEqual(len(vault.vault_roots()), 2)

    def test_racine_de(self):
        self.declarer()
        self.assertEqual(vault.racine_de(SECONDE / "Second.md"), SECONDE.resolve())
        self.assertEqual(vault.racine_de(VAULT / "Alpha.md"), VAULT.resolve())
        self.assertIsNone(vault.racine_de(DEHORS / "Prive.md"))

    def test_corbeille_et_versions_suivent_leur_racine(self):
        """Un fichier d'une racine secondaire ne part pas dans la corbeille d'une autre."""
        self.declarer()
        cible = SECONDE / "Jetable.md"
        cible.write_text("# Jetable\n", encoding="utf-8")
        parti = vault.to_trash(cible)
        self.assertTrue(str(parti).startswith(str(SECONDE)), parti)
        autre = SECONDE / "Second.md"
        version = vault.snapshot(autre, force=True)
        self.assertTrue(str(version).startswith(str(SECONDE)), version)


# ── Les agents ne suivent pas ────────────────────────────────────────────
class TestAgentsBornes(RacinesBase):
    def setUp(self):
        super().setUp()
        for ident in [c["id"] for c in cles.lister()]:
            data = cles._lire(); data.pop(ident, None); cles._ecrire(data)
        self.declarer()

    def cle(self, droits=None):
        d = self.post("/api/agents/cles", json_droits(droits)).get_json()
        return d["info"]["id"], {"X-Prisme-Cle": d["cle"]}

    def test_une_cle_ne_voit_que_la_principale(self):
        _ident, entetes = self.cle()
        r = self.c.get("/api/v1/note", headers=entetes,
                       query_string={"path": str(SECONDE / "Second.md")})
        self.assertEqual(r.status_code, 403, "une racine secondaire n'est pas acquise d'office")
        r = self.c.get("/api/v1/note", headers=entetes, query_string={"path": "Alpha.md"})
        self.assertEqual(r.status_code, 200)

    def test_droit_toutes_racines_accorde_au_cas_par_cas(self):
        ident, entetes = self.cle()
        cles.changer_droits(ident, ["lecture", "toutes_racines"])
        r = self.c.get("/api/v1/note", headers=entetes,
                       query_string={"path": str(SECONDE / "Second.md")})
        self.assertEqual(r.status_code, 200)

    def test_meme_avec_le_droit_le_dehors_reste_refuse(self):
        ident, entetes = self.cle()
        cles.changer_droits(ident, ["lecture", "toutes_racines"])
        r = self.c.get("/api/v1/note", headers=entetes,
                       query_string={"path": str(DEHORS / "Prive.md")})
        self.assertEqual(r.status_code, 403)

    def test_l_ecriture_d_un_agent_reste_bornee(self):
        ident, entetes = self.cle()
        cles.changer_droits(ident, ["lecture", "ecriture"])
        r = self.c.post("/api/v1/note", headers=entetes,
                        json={"path": str(SECONDE / "Intrus.md"), "contenu": "# x"})
        self.assertEqual(r.status_code, 403)
        self.assertFalse((SECONDE / "Intrus.md").exists())


def json_droits(droits):
    return {"nom": "Agent E12", "droits": droits or ["lecture", "proposition"]}


# ── Explorateur et routes ───────────────────────────────────────────────
class TestExplorateur(RacinesBase):
    def test_hors_racines_dossiers_seulement(self):
        d = self.get("/api/files", query_string={"path": str(DEHORS)})
        self.assertTrue(d["outside_vault"])
        self.assertEqual([i for i in d["items"] if not i["is_dir"]], [],
                         "aucun nom de fichier hors des racines")

    def test_dans_une_racine_secondaire_les_fichiers_apparaissent(self):
        self.declarer()
        d = self.get("/api/files", query_string={"path": str(SECONDE)})
        self.assertFalse(d["outside_vault"])
        self.assertIn("Second.md", [i["name"] for i in d["items"]])
        self.assertEqual(d["racine"], str(SECONDE))
        self.assertEqual(len(d["racines"]), 2)
        self.assertTrue(d["racines"][0]["principale"])

    def test_lire_une_note_de_la_seconde_racine(self):
        self.declarer()
        d = self.get("/api/files/read", query_string={"path": str(SECONDE / "Second.md")})
        self.assertIn("mot-rare-second", d["content"])

    def test_lire_hors_racines_refuse(self):
        self.declarer()
        r = self.c.get("/api/files/read", headers=self.h,
                       query_string={"path": str(DEHORS / "Prive.md")})
        self.assertEqual(r.status_code, 403)


class TestRoutesRacines(RacinesBase):
    def test_ajouter_puis_retirer(self):
        r = self.post("/api/racines", {"chemin": str(SECONDE)})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.get_json()["racines"]), 2)
        self.assertEqual(self.post("/api/racines/retirer", {"chemin": str(SECONDE)}).status_code, 200)
        self.assertEqual(len(self.get("/api/racines")["racines"]), 1)

    def test_dossier_introuvable_refuse(self):
        r = self.post("/api/racines", {"chemin": str(Path(TMP) / "nexistepas")})
        self.assertEqual(r.status_code, 404)

    def test_doublon_et_imbrication_refuses(self):
        self.post("/api/racines", {"chemin": str(SECONDE)})
        self.assertEqual(self.post("/api/racines", {"chemin": str(SECONDE)}).status_code, 409)
        self.assertEqual(self.post("/api/racines", {"chemin": str(VAULT / "sous")}).status_code, 409)

    def test_la_principale_ne_se_retire_pas(self):
        r = self.post("/api/racines/retirer", {"chemin": str(VAULT)})
        self.assertEqual(r.status_code, 400)

    def test_promouvoir_une_racine(self):
        self.post("/api/racines", {"chemin": str(SECONDE)})
        self.post("/api/racines/principale", {"chemin": str(SECONDE)})
        racines = vault.vault_roots()
        self.assertEqual(racines[0], SECONDE.resolve())
        self.assertIn(VAULT.resolve(), racines, "l'ancienne principale reste déclarée")


# ── Recherche multi-racines ─────────────────────────────────────────────
class TestRecherche(RacinesBase):
    def test_la_recherche_couvre_les_deux_racines(self):
        self.declarer()
        for r in vault.vault_roots():
            get_index(r).refresh(blocking=True)
        d = self.get("/api/search", query_string={"q": "mot-unique"})
        self.assertTrue(d["results"], "la note de la principale")
        d = self.get("/api/search", query_string={"q": "mot-rare-second"})
        self.assertTrue(d["results"], "la note de la seconde racine")
        self.assertEqual(d["results"][0]["racine"], str(SECONDE))

    def test_chaque_racine_a_son_index(self):
        self.declarer()
        a = get_index(VAULT).db_path
        b = get_index(SECONDE).db_path
        self.assertNotEqual(a, b)
        d = self.get("/api/index/status")
        self.assertEqual(len(d["racines"]), 2)

    def test_un_dossier_hors_racines_reste_refuse(self):
        self.declarer()
        r = self.c.get("/api/search", headers=self.h,
                       query_string={"q": "x", "dir": str(DEHORS)})
        self.assertEqual(r.status_code, 403, "meme avec une requete trop courte")

    def test_reconstruire_une_seule_racine(self):
        self.declarer()
        d = self.post("/api/index/rebuild", {"racine": str(SECONDE)}).get_json()
        self.assertEqual(len(d["racines"]), 1)
        self.assertEqual(d["racines"][0]["racine"], str(SECONDE))
        r = self.post("/api/index/rebuild", {"racine": str(DEHORS)})
        self.assertEqual(r.status_code, 404)


# ── Interface ───────────────────────────────────────────────────────────
class TestInterface(unittest.TestCase):
    def setUp(self):
        self.web = ROOT / "prisme_core" / "web"
        self.html = (self.web / "index.html").read_text(encoding="utf-8")

    def test_page_cablee(self):
        for attendu in ('src="/static/js/racines.js"', 'id="rac-liste"', 'id="fp-racines"',
                        'onclick="ajouterRacineCourante()"'):
            self.assertIn(attendu, self.html, attendu)

    def test_racines_js_avant_explorer(self):
        self.assertLess(self.html.index("racines.js"), self.html.index("explorer.js"))

    def test_aucun_popup_du_navigateur(self):
        js = (self.web / "js" / "racines.js").read_text(encoding="utf-8")
        propre = js.replace("confirmer(", "").replace("demanderTexte(", "")
        for interdit in ("alert(", "confirm(", "prompt("):
            self.assertNotIn(interdit, propre)


if __name__ == "__main__":
    unittest.main()
