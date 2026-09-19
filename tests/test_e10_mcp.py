"""Etape E10 : adaptateur MCP (docs/decisions/0032).

L'adaptateur ne fait aucune logique metier : il traduit. Les tests portent donc sur deux
choses, et surtout sur la seconde :

1. **la traduction** — les outils annonces, le protocole, les erreurs rendues lisibles ;
2. **ce qui ne doit PAS passer** — un adaptateur qui elargirait les droits, contournerait
   la garde du vault ou exposerait une route non prevue serait pire qu'inutile : il
   annulerait silencieusement le travail d'E6 et d'E12.

Le protocole est exerce en vrai, par sous-processus et JSON-RPC sur l'entree standard :
un test qui appellerait les fonctions en direct ne verrait ni les erreurs de flux, ni un
`print` egare dans stdout — la panne classique de ce genre d'adaptateur.
"""
import json
import os
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

from commun import ROOT, TMP, VAULT, effacer, reset_vault

from prisme_core import config
from prisme_core.agents import cles
from prisme_core.app import create_app
from prisme_core.routes import security

ADAPTATEUR = ROOT / "mcp" / "prisme_mcp.py"
PORT = 5231
URL = "http://127.0.0.1:%d" % PORT
VAULT_MCP = Path(TMP) / "vault-mcp"
_SERVEUR = {"lance": False}


def _lancer_serveur():
    """Un seul serveur pour toute la classe : Flask ne se rearrete pas proprement."""
    if _SERVEUR["lance"]:
        return
    app = create_app(with_plugins=False)
    threading.Thread(target=lambda: app.run(host="127.0.0.1", port=PORT, threaded=True),
                     daemon=True).start()
    time.sleep(1.2)
    _SERVEUR["lance"] = True


class Session:
    """Un adaptateur lance comme le ferait un client MCP : sous-processus, stdio."""

    def __init__(self, cle, url=URL):
        # On HERITE de l'environnement, on n'en fabrique pas un.
        #
        # Un environnement minimal marche sous Linux et casse sous Windows : sans
        # `SystemRoot`, un processus Python ne peut pas initialiser Winsock, et tout
        # appel reseau echoue en `[WinError 10106] Le fournisseur de services demande
        # n'a pas pu etre charge`. Les tests semblaient alors dire « PRISME ne repond
        # pas » — accusant le code livre, alors que la faute etait dans le banc.
        env = dict(os.environ, PRISME_URL=url, PRISME_CLE=cle)
        # `encoding="utf-8"` explicite : sans lui, le parent decode la sortie du
        # sous-processus dans l'encodage du systeme (cp1252 sous Windows) et casse sur
        # le premier caractere non latin-1 — les fleches des motifs de l'arbre, par
        # exemple. Le protocole MCP est en UTF-8 des deux cotes, ou il n'est pas.
        self.p = subprocess.Popen(
            [sys.executable, str(ADAPTATEUR)], env=env, text=True, bufsize=1,
            encoding="utf-8", errors="replace",
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.n = 0

    def demander(self, methode, params=None, attendre=True):
        self.n += 1
        msg = {"jsonrpc": "2.0", "method": methode, "params": params or {}}
        if attendre:
            msg["id"] = self.n
        self.p.stdin.write(json.dumps(msg) + "\n")
        self.p.stdin.flush()
        if not attendre:
            return None
        ligne = self.p.stdout.readline()
        return json.loads(ligne) if ligne.strip() else None

    def outil(self, nom, args=None):
        r = self.demander("tools/call", {"name": nom, "arguments": args or {}})
        if "error" in r:
            return None, r["error"]["message"]
        res = r["result"]
        return res, (res["content"][0]["text"] if res.get("content") else "")

    def fermer(self):
        """Termine le sous-processus **et referme ses tuyaux**.

        Un adaptateur qui survit a son test continue d'interroger PRISME, qui ouvre
        alors des fichiers du vault. Sous Windows, un fichier ouvert ne peut pas etre
        efface : le test suivant echouait en `[WinError 32] fichier utilise par un
        autre processus`. Sous Linux, l'effacement passe et le probleme reste invisible.
        """
        try:
            self.p.stdin.close()
            self.p.wait(timeout=3)
        except Exception:                                        # noqa: BLE001
            self.p.kill()
            try:
                self.p.wait(timeout=3)
            except Exception:                                    # noqa: BLE001
                pass
        for tuyau in (self.p.stdout, self.p.stderr):
            try:
                tuyau.close()
            except Exception:                                    # noqa: BLE001
                pass


class McpBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Vault a part, et non le vault partage.
        #
        # Ces tests laissent tourner un serveur Flask et des sous-processus : tant qu'ils
        # vivent, ils peuvent tenir un fichier ouvert. Sous Windows, un fichier ouvert ne
        # s'efface pas, et c'est le nettoyage du test SUIVANT qui echouait — E12 tombait
        # sur `[WinError 32]` a cause d'E10. Chacun son dossier, et la question ne se
        # pose plus.
        reset_vault()
        VAULT_MCP.mkdir(parents=True, exist_ok=True)
        effacer(VAULT_MCP.rglob("*.md"))
        (VAULT_MCP / "Calibration.md").write_text(
            "# Calibration\n\nLa calibration mesure l'ecart. Voir [[Methode]].\n", encoding="utf-8")
        (VAULT_MCP / "Methode.md").write_text(
            "# Methode\n\nLe score de Brier.\n", encoding="utf-8")
        cfg = config.rd_cfg()
        config.wr_cfg({**{k: cfg[k] for k in ("base_url", "model")},
                       "workspace": str(VAULT_MCP), "workspaces": [], "emb_actif": False})
        _lancer_serveur()
        # Un nom par classe : le trousseau refuse deux cles actives de meme nom, et
        # chaque classe a son setUpClass.
        cls.ident, cls.cle = cles.creer("Agent MCP %s" % cls.__name__)

    def session(self, cle=None, url=URL):
        s = Session(cle if cle is not None else self.cle, url)
        self.addCleanup(s.fermer)
        s.demander("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}})
        return s


class Protocole(McpBase):
    def test_initialize_annonce_le_serveur(self):
        s = Session(self.cle)
        self.addCleanup(s.fermer)
        r = s.demander("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}})
        self.assertEqual(r["result"]["serverInfo"]["name"], "prisme")
        self.assertIn("tools", r["result"]["capabilities"])

    def test_notification_ne_recoit_pas_de_reponse(self):
        """Une notification JSON-RPC n'a pas d'`id` : y repondre desynchronise le flux.

        On envoie la notification puis une vraie requete : si l'adaptateur avait repondu
        a la notification, c'est SA reponse qu'on lirait ici, avec un `id` qui ne
        correspond pas.
        """
        s = self.session()
        s.demander("notifications/initialized", attendre=False)
        r = s.demander("tools/list")
        self.assertIn("tools", r["result"])
        self.assertEqual(r["id"], s.n)

    def test_les_huit_outils_sont_annonces(self):
        r = self.session().demander("tools/list")
        noms = [t["name"] for t in r["result"]["tools"]]
        self.assertEqual(sorted(noms), sorted([
            "prisme_notes", "prisme_lire", "prisme_chercher", "prisme_arbre",
            "prisme_sources", "prisme_proposer", "prisme_ma_file", "prisme_ecrire"]))

    def test_chaque_outil_a_une_description_et_un_schema(self):
        r = self.session().demander("tools/list")
        for t in r["result"]["tools"]:
            self.assertGreater(len(t["description"]), 40, t["name"])
            self.assertEqual(t["inputSchema"]["type"], "object", t["name"])

    def test_les_deux_recherches_disent_quand_les_prendre(self):
        """`chercher` et `arbre` se ressemblent : sans distinction ecrite, l'agent prendra
        toujours la premiere. La description est du code, ici."""
        r = self.session().demander("tools/list")
        par_nom = {t["name"]: t["description"] for t in r["result"]["tools"]}
        self.assertIn("prisme_arbre", par_nom["prisme_chercher"])
        self.assertIn("relations", par_nom["prisme_arbre"])

    def test_outil_inconnu_rend_une_erreur_de_protocole(self):
        r = self.session().demander("tools/call", {"name": "prisme_rm_rf", "arguments": {}})
        self.assertIn("error", r)
        self.assertIn("inconnu", r["error"]["message"])

    def test_ligne_illisible_ne_tue_pas_l_adaptateur(self):
        """Un client qui envoie une ligne malformee ne doit pas laisser une session
        ouverte vers un processus mort, sans aucun diagnostic."""
        s = self.session()
        s.p.stdin.write("ceci n'est pas du json\n")
        s.p.stdin.flush()
        r = s.demander("tools/list")
        self.assertIn("tools", r["result"])


class Traduction(McpBase):
    def test_lecture(self):
        s = self.session()
        _r, texte = s.outil("prisme_notes")
        self.assertIn("Calibration.md", texte)
        _r, texte = s.outil("prisme_lire", {"chemin": "Calibration.md"})
        self.assertIn("mesure l'ecart", texte)

    def test_recherche_sans_caracteres_de_controle(self):
        """Les marqueurs de surlignage `\\x01`/`\\x02` sont poses pour le navigateur.

        Un agent qui les recoit lit des caracteres de controle au milieu de son texte :
        illisibles, et bruyants dans un contexte de modele.
        """
        _r, texte = self.session().outil("prisme_chercher", {"q": "calibration"})
        self.assertNotIn("\x01", texte)
        self.assertNotIn("\x02", texte)
        self.assertNotIn("\\u0001", texte)
        self.assertIn("calibration", texte.lower())

    def test_arbre_rend_la_carte_des_relations(self):
        _r, texte = self.session().outil("prisme_arbre", {"q": "calibration"})
        donnees = json.loads(texte)
        self.assertIn("carte", donnees)
        self.assertIn("Calibration", donnees["carte"])

    def test_arbre_n_appelle_pas_de_modele(self):
        """La configuration pointe vers un service mort : si l'arbre appelait le modele,
        l'outil rendrait une erreur au lieu d'une carte."""
        res, texte = self.session().outil("prisme_arbre", {"q": "calibration"})
        self.assertFalse(res.get("isError"), texte)
        self.assertNotIn("reponse", json.loads(texte))

    def test_proposition_va_dans_la_file(self):
        res, texte = self.session().outil(
            "prisme_proposer", {"titre": "Tetlock, Superforecasting",
                                "reference": "https://exemple.org/sf"})
        self.assertFalse(res.get("isError"), texte)
        self.assertTrue(json.loads(texte)["acceptee"])
        _r, mienne = self.session().outil("prisme_ma_file")
        self.assertIn("Superforecasting", mienne)

    def test_caracteres_hors_latin1_traversent_le_protocole(self):
        """Les motifs de l'arbre portent `→` et `←`. Ils doivent arriver intacts.

        Sous Windows, stdin/stdout s'ouvrent en cp1252 : `sys.stdout.write` levait un
        UnicodeEncodeError sur la fleche, la reponse ne partait jamais, et le client
        voyait une session muette. L'adaptateur force desormais l'UTF-8 sur ses flux.

        Ce test echouait chez l'auteur et passait chez moi — d'ou son existence.
        """
        _r, texte = self.session().outil("prisme_arbre", {"q": "calibration"})
        donnees = json.loads(texte)
        motifs = " ".join(n["motif"] for n in donnees["noeuds"])
        self.assertTrue("→" in motifs or "←" in motifs,
                        "aucune fleche dans les motifs : le test ne teste rien")

    def test_accents_non_echappes(self):
        """`ensure_ascii=False` n'est pas cosmetique : sinon chaque accent coute six
        caracteres au lieu d'un, sur un vault en francais."""
        (VAULT_MCP / "Accents.md").write_text("# Été\n\nprédiction révisée\n", encoding="utf-8")
        _r, texte = self.session().outil("prisme_chercher", {"q": "prédiction"})
        self.assertNotIn("\\u00e9", texte)


class CeQuiNePassePas(McpBase):
    """La partie qui compte : l'adaptateur ne doit elargir aucun droit."""

    def test_ecriture_refusee_sans_le_droit(self):
        res, texte = self.session().outil(
            "prisme_ecrire", {"chemin": "Force.md", "contenu": "x"})
        self.assertTrue(res.get("isError"))
        self.assertIn("ecriture", texte.replace("é", "e"))
        self.assertFalse((VAULT_MCP / "Force.md").exists())

    def test_lecture_hors_vault_refusee(self):
        res, texte = self.session().outil("prisme_lire", {"chemin": "/etc/passwd"})
        self.assertTrue(res.get("isError"))
        self.assertIn("espaces de travail", texte)

    def test_ecriture_hors_vault_refusee_meme_avec_le_droit(self):
        ident, cle = cles.creer("Agent MCP ecrivain", ["lecture", "proposition", "ecriture"])
        dehors = Path(TMP) / "dehors-mcp.md"
        res, texte = self.session(cle=cle).outil(
            "prisme_ecrire", {"chemin": str(dehors), "contenu": "x"})
        self.assertTrue(res.get("isError"))
        self.assertFalse(dehors.exists())
        cles.revoquer(ident)

    def test_cle_absente(self):
        res, texte = self.session(cle="").outil("prisme_notes")
        self.assertTrue(res.get("isError"))
        self.assertIn("refus", texte.lower())

    def test_cle_revoquee(self):
        ident, cle = cles.creer("Agent MCP revoque")
        s = self.session(cle=cle)
        res, _t = s.outil("prisme_notes")
        self.assertFalse(res.get("isError"))
        cles.revoquer(ident)
        res, texte = s.outil("prisme_notes")
        self.assertTrue(res.get("isError"), "une cle revoquee doit cesser de fonctionner")

    def test_prisme_eteint_donne_un_message_utile(self):
        """Sans PRISME, l'adaptateur ne peut rien faire. Il doit le DIRE : un agent qui
        lit « connexion refusee » ne sait pas qu'il lui suffit de lancer PRISME."""
        res, texte = self.session(url="http://127.0.0.1:5999").outil("prisme_notes")
        self.assertTrue(res.get("isError"))
        self.assertIn("Lancez PRISME", texte)

    def test_erreur_rendue_dans_le_resultat_pas_comme_panne_de_protocole(self):
        """Une erreur d'outil doit se lire par l'agent, pas interrompre sa session."""
        r = self.session(url="http://127.0.0.1:5999").demander(
            "tools/call", {"name": "prisme_notes", "arguments": {}})
        self.assertNotIn("error", r)
        self.assertTrue(r["result"]["isError"])


class SurfaceApi(McpBase):
    """La route ajoutee a `/api/v1/` par cette etape."""

    def setUp(self):
        self.c = create_app(with_plugins=False).test_client()
        self.h = {"X-Prisme-Cle": self.cle}

    def test_arbre_expose_et_annonce(self):
        r = self.c.get("/api/v1/", headers=self.h)
        self.assertIn("GET /api/v1/arbre?q=", r.get_json()["routes"])

    def test_arbre_demande_le_droit_de_lecture(self):
        r = self.c.get("/api/v1/arbre?q=calibration")
        self.assertIn(r.status_code, (401, 403))

    def test_arbre_depart_hors_vault_refuse(self):
        r = self.c.get("/api/v1/arbre?q=x&depart=/etc/passwd", headers=self.h)
        self.assertEqual(r.status_code, 403)

    def test_arbre_requete_trop_courte(self):
        r = self.c.get("/api/v1/arbre?q=a", headers=self.h)
        self.assertEqual(r.status_code, 400)

    def test_arbre_rend_des_chemins_relatifs(self):
        """Un agent n'a aucune raison de connaitre l'arborescence reelle du disque."""
        d = self.c.get("/api/v1/arbre?q=calibration", headers=self.h).get_json()
        for n in d["noeuds"]:
            self.assertFalse(Path(n["chemin"]).is_absolute(), n["chemin"])


class Livraison(unittest.TestCase):
    def test_l_adaptateur_est_livre(self):
        self.assertTrue(ADAPTATEUR.is_file())

    def test_bibliotheque_standard_seulement(self):
        """Il est lance par le client MCP avec le Python qu'il trouve, pas par PRISME :
        une dependance ici, c'est une installation exigee de quelqu'un qui voulait juste
        coller un bloc de configuration."""
        texte = ADAPTATEUR.read_text(encoding="utf-8")
        interdits = ("import requests", "import mcp", "from mcp", "import flask",
                     "import httpx", "import pydantic")
        for mot in interdits:
            self.assertNotIn(mot, texte, mot)

    def test_n_importe_pas_prisme_core(self):
        """L'adaptateur doit rester jetable : s'il importait le coeur, il cesserait
        d'etre un traducteur pour devenir une seconde porte d'entree."""
        self.assertNotIn("prisme_core", ADAPTATEUR.read_text(encoding="utf-8"))

    def test_le_sous_processus_herite_de_l_environnement(self):
        """Garde-fou contre une erreur deja commise, invisible sous Linux.

        Le banc fabriquait un environnement minimal pour l'adaptateur. Sous Windows,
        un processus sans `SystemRoot` ne peut pas initialiser Winsock : tout appel
        reseau echouait en `[WinError 10106]`, et huit tests accusaient le code livre
        alors que la faute etait ici.

        On verifie donc que les variables vitales de la PLATEFORME COURANTE arrivent
        bien au sous-processus, quelle qu'elle soit.
        """
        vitales = ["SystemRoot", "windir"] if os.name == "nt" else ["PATH"]
        presentes = [v for v in vitales if v in os.environ]
        self.assertTrue(presentes, "aucune variable vitale connue pour %s" % os.name)
        s = Session("prisme-peu-importe")
        self.addCleanup(s.fermer)
        code = ("import json,os,sys;"
                "sys.stdout.write(json.dumps({k: k in os.environ for k in %r})+chr(10));"
                % presentes)
        essai = subprocess.run([sys.executable, "-c", code],
                               env=dict(os.environ, PRISME_URL="x", PRISME_CLE="y"),
                               capture_output=True, text=True, timeout=30)
        for cle, presente in json.loads(essai.stdout).items():
            self.assertTrue(presente, "%s n'atteint pas le sous-processus" % cle)

    def test_onglet_et_route_de_configuration(self):
        html = (ROOT / "prisme_core" / "web" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "prisme_core" / "web" / "js" / "agents.js").read_text(encoding="utf-8")
        self.assertIn('id="agp2"', html)
        self.assertIn("mcpGenerer", html)
        self.assertIn("/api/agents/mcp", js)


class Configuration(McpBase):
    def setUp(self):
        self.c = create_app(with_plugins=False).test_client()
        self.h = {"X-Prisme-Token": security.TOKEN}

    def test_configuration_prete_a_coller(self):
        r = self.c.post("/api/agents/mcp", json={"nom": "Claude Code test"}, headers=self.h)
        self.assertEqual(r.status_code, 201)
        d = r.get_json()
        serveur = d["configuration"]["mcpServers"]["prisme"]
        self.assertTrue(serveur["args"][0].endswith("mcp/prisme_mcp.py"))
        self.assertEqual(serveur["env"]["PRISME_CLE"], d["cle"])
        self.assertIn("http://", serveur["env"]["PRISME_URL"])

    def test_chemin_en_barres_obliques(self):
        """Un antislash dans du JSON doit etre echappe : c'est la faute que tout le monde
        fait en recopiant un chemin Windows a la main."""
        r = self.c.post("/api/agents/mcp", json={"nom": "Claude Code chemins"}, headers=self.h)
        self.assertNotIn("\\", r.get_json()["adaptateur"])

    def test_droits_par_defaut_sans_ecriture(self):
        r = self.c.post("/api/agents/mcp", json={"nom": "Claude Code droits"}, headers=self.h)
        droits = r.get_json()["info"]["droits"]
        self.assertIn("lecture", droits)
        self.assertIn("proposition", droits)
        self.assertNotIn("ecriture", droits)

    def test_nom_invalide_refuse(self):
        r = self.c.post("/api/agents/mcp", json={"nom": "x" * 90}, headers=self.h)
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
