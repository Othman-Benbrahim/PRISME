"""Etape E6 : API locale a cles pour les agents exterieurs (docs/decisions/0018)."""
import re
import unittest
from pathlib import Path

from commun import ROOT, TMP, VAULT, reset_vault

from prisme_core import frontmatter
from prisme_core.agents import cles, journal
from prisme_core.app import create_app
from prisme_core.objets import file as filedattente
from prisme_core.routes import security


class AgentsBase(unittest.TestCase):
    def setUp(self):
        reset_vault()
        journal.vider()
        for ident in [c["id"] for c in cles.lister()]:
            data = cles._lire()
            data.pop(ident, None)
            cles._ecrire(data)
        filedattente.vider()
        for c in list(filedattente.rejets()):
            filedattente.oublier_rejet(c)
        self.c = create_app(with_plugins=False).test_client()
        self.h = {"X-Prisme-Token": security.TOKEN}

    def nouvelle_cle(self, nom="Agent", droits=None):
        d = self.c.post("/api/agents/cles", headers=self.h,
                        json={"nom": nom, "droits": droits or list(cles.DROITS_DEFAUT)}).get_json()
        return d["info"]["id"], d["cle"], {"X-Prisme-Cle": d["cle"]}


# ── Trousseau ───────────────────────────────────────────────────────────
class TestTrousseau(AgentsBase):
    def test_la_cle_n_est_donnee_qu_une_fois(self):
        ident, cle, _ = self.nouvelle_cle()
        stocke = cles._lire()[ident]
        self.assertNotIn(cle, str(stocke), "la cle en clair ne doit pas etre stockee")
        self.assertEqual(stocke["empreinte"], cles.empreinte(cle))
        self.assertNotIn("empreinte", cles.par_id(ident), "l'empreinte ne ressort pas par l'API")
        self.assertTrue(cles.par_id(ident)["indice"].startswith(cles.PREFIXE))

    def test_droits_par_defaut(self):
        ident, _, _ = self.nouvelle_cle()
        self.assertEqual(cles.par_id(ident)["droits"], ["lecture", "proposition"],
                         "l'ecriture n'est jamais accordee par defaut (0018)")

    def test_lecture_toujours_presente(self):
        ident, _, _ = self.nouvelle_cle(droits=["proposition"])
        self.assertIn("lecture", cles.par_id(ident)["droits"])

    def test_nom_invalide_et_doublon(self):
        with self.assertRaises(cles.CleInvalide):
            cles.creer("x")
        cles.creer("Veille")
        with self.assertRaises(cles.CleInvalide):
            cles.creer("veille")

    def test_verification(self):
        ident, cle, _ = self.nouvelle_cle()
        self.assertEqual(cles.verifier(cle)[0], ident)
        self.assertIsNone(cles.verifier("prisme-faux")[0])
        self.assertIsNone(cles.verifier("")[0])

    def test_revocation_puis_oubli(self):
        ident, cle, _ = self.nouvelle_cle()
        cles.revoquer(ident)
        self.assertIsNone(cles.verifier(cle)[0])
        with self.assertRaises(cles.CleInvalide):
            cles.revoquer(ident)
        self.assertTrue(cles.oublier(ident)["ok"])
        self.assertIsNone(cles.par_id(ident))

    def test_oubli_refuse_avant_revocation(self):
        ident, _, _ = self.nouvelle_cle()
        with self.assertRaises(cles.CleInvalide):
            cles.oublier(ident)

    def test_deux_cles_sont_differentes(self):
        _, a, _ = self.nouvelle_cle("Un")
        _, b, _ = self.nouvelle_cle("Deux")
        self.assertNotEqual(a, b)
        self.assertGreater(len(a), 40, "32 octets d'alea au moins")


# ── Authentification ────────────────────────────────────────────────────
class TestGarde(AgentsBase):
    def test_sans_cle_ni_jeton(self):
        self.assertEqual(self.c.get("/api/v1/ping").status_code, 401)

    def test_le_jeton_de_session_ne_vaut_pas_cle(self):
        """La surface des agents a sa propre authentification : le jeton du navigateur
        n'y donne pas acces, sinon une page ouverte vaudrait une cle d'agent."""
        self.assertEqual(self.c.get("/api/v1/ping", headers=self.h).status_code, 401)

    def test_cle_inconnue_puis_valide(self):
        _, _, a = self.nouvelle_cle()
        self.assertEqual(self.c.get("/api/v1/ping", headers={"X-Prisme-Cle": "prisme-faux"}).status_code, 403)
        self.assertEqual(self.c.get("/api/v1/ping", headers=a).status_code, 200)

    def test_bearer_accepte(self):
        _, cle, _ = self.nouvelle_cle()
        r = self.c.get("/api/v1/ping", headers={"Authorization": "Bearer " + cle})
        self.assertEqual(r.status_code, 200)

    def test_cle_revoquee_refusee(self):
        ident, _, a = self.nouvelle_cle()
        self.assertEqual(self.c.get("/api/v1/ping", headers=a).status_code, 200)
        cles.revoquer(ident)
        r = self.c.get("/api/v1/ping", headers=a)
        self.assertEqual(r.status_code, 403)
        self.assertIn("révoquée", r.get_json()["error"])

    def test_no_auth_n_ouvre_pas_la_surface_agent(self):
        """PRISME_NO_AUTH dispense du jeton de session, jamais de la cle d'agent."""
        security.NO_AUTH = True
        try:
            self.assertEqual(self.c.get("/api/files?dir=", headers={}).status_code, 200)
            self.assertEqual(self.c.get("/api/v1/ping").status_code, 401)
        finally:
            security.NO_AUTH = False

    def test_hote_non_local_refuse_avant_tout(self):
        _, _, a = self.nouvelle_cle()
        r = self.c.get("/api/v1/ping", headers={**a, "Host": "exemple.com"})
        self.assertEqual(r.status_code, 403)
        self.assertIn("Hôte", r.get_json()["error"])

    def test_usage_compte(self):
        ident, _, a = self.nouvelle_cle()
        self.c.get("/api/v1/ping", headers=a)
        self.c.get("/api/v1/ping", headers=a)
        info = cles.par_id(ident)
        self.assertEqual(info["appels"], 2)
        self.assertTrue(info["derniere_utilisation"])


# ── Lecture ─────────────────────────────────────────────────────────────
class TestLecture(AgentsBase):
    def setUp(self):
        super().setUp()
        self.ident, self.cle, self.a = self.nouvelle_cle()

    def test_ping_decrit_la_surface(self):
        d = self.c.get("/api/v1/ping", headers=self.a).get_json()
        self.assertEqual(d["agent"], "Agent")
        self.assertEqual(d["droits"], ["lecture", "proposition"])
        self.assertIn("GET /api/v1/recherche?q=", d["routes"])

    def test_notes_et_note(self):
        d = self.c.get("/api/v1/notes", headers=self.a).get_json()
        chemins = [n["chemin"] for n in d["notes"]]
        self.assertIn("Alpha.md", chemins)
        self.assertIn("sous/Beta.md", chemins, "chemins en barres obliques")
        d = self.c.get("/api/v1/note?path=Alpha.md", headers=self.a).get_json()
        self.assertIn("mot-unique", d["contenu"])

    def test_note_hors_vault_refusee(self):
        r = self.c.get("/api/v1/note?path=" + str(TMP / "dehors.md"), headers=self.a)
        self.assertEqual(r.status_code, 403)

    def test_note_absente(self):
        self.assertEqual(self.c.get("/api/v1/note?path=Rien.md", headers=self.a).status_code, 404)

    def test_recherche(self):
        d = self.c.get("/api/v1/recherche?q=mot-unique", headers=self.a).get_json()
        self.assertTrue(d["resultats"])
        self.assertEqual(self.c.get("/api/v1/recherche?q=a", headers=self.a).status_code, 400)


# ── Proposition ─────────────────────────────────────────────────────────
class TestProposition(AgentsBase):
    def setUp(self):
        super().setUp()
        self.ident, self.cle, self.a = self.nouvelle_cle("Veille arXiv")

    def test_depot_dans_la_file_pas_dans_le_vault(self):
        from prisme_core.objets import sources
        r = self.c.post("/api/v1/proposer", headers=self.a,
                        json={"titre": "Rapport K", "note": "Alpha.md", "motif": "cité"})
        self.assertEqual(r.status_code, 201)
        entree = r.get_json()["entree"]
        self.assertEqual(entree["origine"], "agent:Veille arXiv")
        self.assertEqual(entree["note"], "Alpha.md")
        self.assertEqual(len(filedattente.lister()), 1)
        self.assertEqual(sources.lister(), [], "rien n'entre dans le vault (0018)")

    def test_meme_une_reference_verifiable_passe_par_la_file(self):
        """0021 : les propositions d'agents ne beneficient jamais de l'entree directe."""
        from prisme_core.objets import sources
        r = self.c.post("/api/v1/proposer", headers=self.a,
                        json={"titre": "Papier", "reference": "https://arxiv.org/abs/2401.09876"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["entree"]["cle"], "arxiv:2401.09876")
        self.assertEqual(r.get_json()["entree"]["genre"], "arxiv")
        self.assertEqual(sources.lister(), [])

    def test_doublon_refuse(self):
        self.c.post("/api/v1/proposer", headers=self.a, json={"titre": "Rapport K"})
        r = self.c.post("/api/v1/proposer", headers=self.a, json={"titre": "Rapport K"})
        self.assertEqual(r.status_code, 409)
        self.assertFalse(r.get_json()["acceptee"])

    def test_rejet_memorise_bloque_l_agent(self):
        self.c.post("/api/v1/proposer", headers=self.a, json={"titre": "Rapport K"})
        cle = filedattente.lister()[0]["cle"]
        filedattente.rejeter(cle, "hors sujet")
        self.assertEqual(self.c.post("/api/v1/proposer", headers=self.a,
                                     json={"titre": "Rapport K"}).status_code, 409)

    def test_titre_requis(self):
        self.assertEqual(self.c.post("/api/v1/proposer", headers=self.a, json={}).status_code, 400)

    def test_plafond_par_cle(self):
        """Le plafond par origine d'E5 devient un plafond par cle."""
        origine = "agent:Veille arXiv"
        for i in range(filedattente.PLAFOND_PAR_ORIGINE):
            filedattente.ajouter({"cle": "texte:t%d" % i, "origine": origine})
        self.assertEqual(self.c.post("/api/v1/proposer", headers=self.a,
                                     json={"titre": "Un de trop"}).status_code, 409)
        _, _, autre = self.nouvelle_cle("Autre agent")
        self.assertEqual(self.c.post("/api/v1/proposer", headers=autre,
                                     json={"titre": "Un de trop"}).status_code, 201)

    def test_un_agent_ne_voit_que_sa_file(self):
        self.c.post("/api/v1/proposer", headers=self.a, json={"titre": "A moi"})
        _, _, autre = self.nouvelle_cle("Autre")
        self.c.post("/api/v1/proposer", headers=autre, json={"titre": "A lui"})
        mienne = self.c.get("/api/v1/file", headers=self.a).get_json()
        self.assertEqual([e["titre"] for e in mienne["entrees"]], ["A moi"])


# ── Ecriture ────────────────────────────────────────────────────────────
class TestEcriture(AgentsBase):
    def test_refusee_sans_le_droit(self):
        _, _, a = self.nouvelle_cle()
        r = self.c.post("/api/v1/note", headers=a, json={"path": "X.md", "contenu": "# X"})
        self.assertEqual(r.status_code, 403)
        self.assertIn("ecriture", r.get_json()["error"])
        self.assertFalse((VAULT / "X.md").exists())

    def test_accordee_puis_estampillee(self):
        ident, _, a = self.nouvelle_cle("Redacteur", ["lecture", "proposition", "ecriture"])
        r = self.c.post("/api/v1/note", headers=a, json={"path": "X.md", "contenu": "# X\n\ncorps"})
        self.assertEqual(r.status_code, 201)
        meta = frontmatter.parse((VAULT / "X.md").read_text(encoding="utf-8"))
        self.assertEqual(meta["prisme_outil"], "agent")
        self.assertEqual(meta["prisme_genere_par"], "Redacteur")
        self.assertEqual(meta["prisme_agent_cle"], ident)
        self.assertTrue(meta["prisme_id"], "une note de machine porte un identifiant des sa creation")

    def test_ecrasement_garde_une_version(self):
        _, _, a = self.nouvelle_cle("Redacteur", ["lecture", "ecriture"])
        (VAULT / "X.md").write_text("# Ancien\n", encoding="utf-8")
        r = self.c.post("/api/v1/note", headers=a, json={"path": "X.md", "contenu": "# Neuf"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["remplacee"])
        versions = list((VAULT / ".trash" / "versions").rglob("X_*.md"))
        self.assertTrue(versions, "ce qu'un agent ecrase reste recuperable")
        self.assertIn("Ancien", versions[0].read_text(encoding="utf-8"))

    def test_hors_vault_et_extension(self):
        _, _, a = self.nouvelle_cle("Redacteur", ["lecture", "ecriture"])
        self.assertEqual(self.c.post("/api/v1/note", headers=a,
                                     json={"path": str(TMP / "dehors.md"), "contenu": "x"}).status_code, 403)
        self.assertEqual(self.c.post("/api/v1/note", headers=a,
                                     json={"path": "X.txt", "contenu": "x"}).status_code, 400)
        self.assertEqual(self.c.post("/api/v1/note", headers=a,
                                     json={"path": "X.md", "contenu": ""}).status_code, 400)

    def test_retrait_du_droit(self):
        ident, _, a = self.nouvelle_cle("Redacteur", ["lecture", "ecriture"])
        cles.changer_droits(ident, ["lecture"])
        self.assertEqual(self.c.post("/api/v1/note", headers=a,
                                     json={"path": "X.md", "contenu": "# X"}).status_code, 403)


# ── Journal ─────────────────────────────────────────────────────────────
class TestJournal(AgentsBase):
    def test_tout_appel_laisse_une_trace(self):
        ident, _, a = self.nouvelle_cle("Tracee")
        self.c.get("/api/v1/ping", headers=a)
        self.c.post("/api/v1/note", headers=a, json={"path": "X.md", "contenu": "# X"})
        self.c.get("/api/v1/ping", headers={"X-Prisme-Cle": "prisme-faux"})
        lignes = journal.lire()
        self.assertGreaterEqual(len(lignes), 4, "creation, ping, refus d'ecriture, cle inconnue")
        refus = [l for l in lignes if l["statut"] >= 400]
        self.assertTrue(any(l["chemin"] == "/api/v1/note" for l in refus))
        self.assertTrue(any(l["cle"] == "-" for l in refus), "une cle inconnue est tracee aussi")

    def test_journal_survit_a_la_revocation(self):
        ident, _, a = self.nouvelle_cle("Ephemere")
        self.c.get("/api/v1/ping", headers=a)
        cles.revoquer(ident)
        cles.oublier(ident)
        self.assertTrue([l for l in journal.lire() if l["cle"] == ident],
                        "effacer une cle n'efface pas ce qu'elle a fait")

    def test_filtre_par_cle(self):
        i1, _, a1 = self.nouvelle_cle("Un")
        _, _, a2 = self.nouvelle_cle("Deux")
        self.c.get("/api/v1/ping", headers=a1)
        self.c.get("/api/v1/ping", headers=a2)
        self.assertTrue(all(l["cle"] == i1 for l in journal.lire(cle=i1)))

    def test_ligne_abimee_n_emporte_pas_le_reste(self):
        _, _, a = self.nouvelle_cle()
        self.c.get("/api/v1/ping", headers=a)
        f = journal._fichier()
        f.write_text(f.read_text(encoding="utf-8") + "{ceci n'est pas du json\n", encoding="utf-8")
        self.assertTrue(journal.lire())


# ── Routes de gestion ───────────────────────────────────────────────────
class TestGestion(AgentsBase):
    def test_parcours(self):
        r = self.c.post("/api/agents/cles", headers=self.h, json={"nom": "Veille"})
        self.assertEqual(r.status_code, 201)
        self.assertIn("avertissement", r.get_json())
        ident = r.get_json()["info"]["id"]
        d = self.c.get("/api/agents/cles", headers=self.h).get_json()
        self.assertEqual(len(d["cles"]), 1)
        self.assertEqual(d["droits_defaut"], ["lecture", "proposition"])
        self.assertNotIn("empreinte", d["cles"][0])
        r = self.c.post("/api/agents/cles/droits", headers=self.h,
                        json={"id": ident, "droits": ["lecture", "ecriture"]})
        self.assertEqual(r.get_json()["info"]["droits"], ["lecture", "ecriture"])
        self.assertEqual(self.c.post("/api/agents/cles/revoquer", headers=self.h,
                                     json={"id": ident}).status_code, 200)
        self.assertTrue(self.c.get("/api/agents/journal", headers=self.h).get_json()["lignes"])

    def test_erreurs(self):
        self.assertEqual(self.c.post("/api/agents/cles", headers=self.h, json={"nom": "x"}).status_code, 400)
        self.assertEqual(self.c.post("/api/agents/cles/revoquer", headers=self.h,
                                     json={"id": "ag-inconnu"}).status_code, 404)
        self.assertEqual(self.c.post("/api/agents/cles/droits", headers=self.h,
                                     json={"id": "ag-inconnu"}).status_code, 404)

    def test_gestion_protegee_par_le_jeton(self):
        self.assertEqual(self.c.get("/api/agents/cles").status_code, 403)


# ── Interface ───────────────────────────────────────────────────────────
class TestInterface(unittest.TestCase):
    def setUp(self):
        self.html = (ROOT / "prisme_core" / "web" / "index.html").read_text(encoding="utf-8")

    def test_page_cablee(self):
        for attendu in ('src="/static/js/agents.js"', 'href="/static/css/agents.css"',
                        'id="magents"', 'onclick="openAgents()"', 'id="ag-nouvelle-cle"'):
            self.assertIn(attendu, self.html, attendu)

    def test_aucun_popup_du_navigateur(self):
        js = (ROOT / "prisme_core" / "web" / "js" / "agents.js").read_text(encoding="utf-8")
        propre = js.replace("confirmer(", "").replace("demanderTexte(", "")
        for interdit in ("alert(", "confirm(", "prompt("):
            self.assertNotIn(interdit, propre)

    def test_ordre_des_scripts(self):
        for avant in ("dialogues.js", "helpers.js"):
            self.assertLess(self.html.index(avant), self.html.index("agents.js"), avant)

    def test_le_dialogue_passe_au_dessus_des_fenetres(self):
        """Regression : #mdialog partageait le z-index des autres recouvrements.

        Comme il vient plus tot dans le DOM, la fenetre qui l'ouvrait (Sources, Objets,
        Agents, Plugins) interceptait les clics : le bouton de confirmation etait
        visible mais inerte. Revoquer une cle ou annuler un lot etait impossible.
        """
        css = ROOT / "prisme_core" / "web" / "css"
        commun = re.search(r"\.ov\{[^}]*z-index:\s*(\d+)",
                           (css / "core.css").read_text(encoding="utf-8"))
        dialogue = re.search(r"#mdialog\{[^}]*z-index:\s*(\d+)",
                             (css / "editeur.css").read_text(encoding="utf-8"))
        self.assertIsNotNone(commun, "z-index des recouvrements introuvable")
        self.assertIsNotNone(dialogue, "#mdialog doit fixer son propre z-index")
        self.assertGreater(int(dialogue.group(1)), int(commun.group(1)))


if __name__ == "__main__":
    unittest.main()
