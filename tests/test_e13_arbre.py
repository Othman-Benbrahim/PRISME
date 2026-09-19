"""Etape E13 : recherche en arbre (docs/decisions/0029).

Trois familles de tests, dans l'ordre de ce qui casse le plus cher :

1. **la forme de l'arbre** — pas de cycle, pas d'explosion, plafonds respectes. Un cycle
   est passe en production une fois : une amorce se retrouvait fille de sa propre
   descendante parce qu'un second chemin reattribuait le parent ;
2. **la garde du vault** — la liste « retenus » revient du navigateur et sert a LIRE des
   fichiers. Sans filtre, une requete forgee lirait n'importe quoi ;
3. **la mesure** — la decision 0029 exigeait de mesurer plutot que de supposer, et la
   mesure a corrige la justification de l'etape. Les chiffres sont donc testes, pour que
   personne ne les reecrive a la baisse sans s'en apercevoir.
"""
import unittest
from pathlib import Path

from commun import TMP, VAULT, effacer, reset_vault

from prisme_core import config, index as idxmod, vault
from prisme_core.app import create_app
from prisme_core.arbre import contexte, parcours
from prisme_core.index import fresh_index
from prisme_core.routes import security

DEHORS = Path(TMP) / "dehors-arbre"


def ecrire(nom, texte):
    p = VAULT / nom
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texte, encoding="utf-8")
    return p


class ArbreBase(unittest.TestCase):
    def setUp(self):
        reset_vault()
        effacer(VAULT.rglob("*.md"))
        # Structure de liens connue, avec un aller-retour Methode <-> Calibration :
        # c'est exactement la forme qui produisait un cycle.
        ecrire("Question.md", "# Question\n\nComment calibrer une prevision ? Voir [[Methode]].\n")
        ecrire("Methode.md", "# Methode\n\nLa methode de calibration repose sur Brier.\n")
        ecrire("Calibration.md", "# Calibration\n\nCalibration : voir [[Methode]] et [[Brier]].\n")
        ecrire("Brier.md", "# Brier\n\nLe score de Brier est l'erreur quadratique.\n")
        ecrire("Journal.md", "# Journal\n\nRelu [[Methode]] aujourd'hui.\n")
        ecrire("Cuisine.md", "# Cuisine\n\nRecette de pain au levain.\n")
        cfg = config.rd_cfg()
        config.wr_cfg({**{k: cfg[k] for k in ("workspace", "base_url", "model")},
                       "workspaces": [], "emb_actif": False})
        vault._LAST_SNAP.clear()
        idxmod.forget_all()
        self.idx = fresh_index(VAULT)
        self.idx.refresh()

    def arbre(self, question="calibration Brier", **kw):
        return parcours.construire(self.idx, question, **kw)


class FormeDeLArbre(ArbreBase):
    def test_aucun_cycle(self):
        """Le bug fondateur : une amorce devenue fille de sa propre descendante.

        `Methode` est atteinte par la pertinence (niveau 0) ET par un lien depuis
        `Calibration`. Si le second passage reattribue le parent, l'arbre affiche une
        boucle, et l'assemblage du contexte tourne en rond.
        """
        a = self.arbre()
        parents = {n["chemin"]: n["parent"] for n in a["noeuds"]}
        for depart in parents:
            vus, courant = set(), depart
            while courant:
                self.assertNotIn(courant, vus,
                                 "cycle dans l'arbre en partant de %s" % Path(depart).name)
                vus.add(courant)
                courant = parents.get(courant) or ""

    def test_une_amorce_ne_prend_jamais_de_parent(self):
        a = self.arbre()
        for n in a["noeuds"]:
            if n["niveau"] == 0:
                self.assertEqual(n["parent"], "", "%s (amorce) a un parent" % n["nom"])

    def test_un_chemin_n_apparait_qu_une_fois(self):
        a = self.arbre()
        chemins = [n["chemin"] for n in a["noeuds"]]
        self.assertEqual(len(chemins), len(set(chemins)))

    def test_second_chemin_fait_monter_le_score_sans_deplacer_le_noeud(self):
        """Dedoublonnage : le meilleur des deux scores, mais la place du plus court chemin."""
        a = self.arbre()
        par_nom = {n["nom"]: n for n in a["noeuds"]}
        m = par_nom["Methode.md"]
        self.assertEqual(m["niveau"], 0)
        # atteinte aussi par un lien depuis Calibration : son score depasse la seule pertinence
        self.assertGreaterEqual(m["score"], m["pertinence"])

    def test_profondeur_bornee(self):
        a = self.arbre(profondeur=1)
        self.assertTrue(all(n["niveau"] <= 1 for n in a["noeuds"]))

    def test_plafond_par_niveau(self):
        """Une note-carrefour ne doit pas manger le budget a elle seule."""
        cible = ecrire("Carrefour.md", "# Carrefour\n\nmot-carrefour\n\n"
                       + "\n".join("[[Feuille-%02d]]" % i for i in range(40)))
        for i in range(40):
            ecrire("Feuille-%02d.md" % i, "# Feuille %02d\n\nfeuille\n" % i)
        self.idx = fresh_index(VAULT)
        self.idx.refresh()
        a = parcours.construire(self.idx, "mot-carrefour", depart=str(cible), profondeur=1)
        par_lien = [n for n in a["noeuds"] if n["niveau"] == 1]
        self.assertLessEqual(len(par_lien), parcours.PAR_NIVEAU)

    def test_decroissance_avec_la_distance(self):
        a = self.arbre(question="calibration")
        n0 = [n["score"] for n in a["noeuds"] if n["niveau"] == 0]
        n2 = [n["score"] for n in a["noeuds"] if n["niveau"] == 2]
        if n0 and n2:
            self.assertGreater(max(n0), max(n2))

    def _vault_termes_separes(self):
        """Un terme par note, et un lien entre les deux. Le fixture ordinaire ne sert pas :
        `Methode.md` y contient « calibration » ET « Brier », donc la recherche plate
        trouve, et le repli ne se declenche jamais."""
        effacer(VAULT.rglob("*.md"))
        ecrire("Calibration.md", "# Calibration\n\nLa calibration mesure l'ecart. Voir [[Score]].\n")
        ecrire("Score.md", "# Score\n\nErreur quadratique moyenne.\n")
        self.idx = fresh_index(VAULT)
        self.idx.refresh()

    def test_question_a_plusieurs_termes_repartis_sur_plusieurs_notes(self):
        """La recherche lexicale exige TOUS les termes : sans repli, l'arbre sort vide.

        Ici « calibration » est dans une note et « quadratique » dans une autre. La
        recherche plate ne rend rien pour la question entiere — et c'est precisement le
        cas que l'arbre devrait le mieux servir, puisque les deux notes sont reliees.

        Trouve en ecrivant les tests d'E10, pas par ceux d'E13 : le banc de mesure d'E13
        utilisait des notes ou tous les termes coexistaient.
        """
        from prisme_core.index import search as lexical
        self._vault_termes_separes()
        self.assertEqual(len(lexical.search(self.idx, "calibration quadratique", limit_files=40)), 0,
                         "si la recherche plate trouve, ce test ne teste plus le repli")
        a = self.arbre("calibration quadratique")
        self.assertTrue(a["noeuds"], "l'arbre ne doit pas sortir vide")
        self.assertTrue(a["recherche"].get("repli_par_terme"),
                        "le repli doit etre signale, pas silencieux")
        self.assertEqual({n["nom"] for n in a["noeuds"]}, {"Calibration.md", "Score.md"})

    def test_le_repli_ne_sert_que_si_la_question_entiere_ne_rend_rien(self):
        self._vault_termes_separes()
        a = self.arbre("calibration")
        self.assertTrue(a["noeuds"])
        self.assertFalse(a["recherche"].get("repli_par_terme"))

    def test_les_amorces_du_repli_pesent_moins(self):
        """Une note qui satisfait un terme sur deux ne vaut pas une note qui les a tous."""
        self._vault_termes_separes()
        entiere = self.arbre("calibration")
        partielle = self.arbre("calibration quadratique")
        self.assertGreater(max(n["pertinence"] for n in entiere["noeuds"]),
                           max(n["pertinence"] for n in partielle["noeuds"]))

    def test_note_ouverte_comme_amorce(self):
        a = parcours.construire(self.idx, "", depart=str(VAULT / "Calibration.md"))
        amorces = [n for n in a["noeuds"] if n["niveau"] == 0]
        self.assertEqual(len(amorces), 1)
        self.assertEqual(amorces[0]["motif"], "note ouverte")
        self.assertIn("Brier.md", [n["nom"] for n in a["noeuds"]])


class Budget(ArbreBase):
    def test_ce_qui_depasse_reste_visible(self):
        """Depasser le budget ne fait pas disparaitre un noeud : il est marque non retenu.

        On doit voir ce qui a ete ecarte, sinon l'elagage se fait sur un arbre deja
        tronque en secret.
        """
        a = self.arbre(budget=60)
        self.assertTrue(any(not n["retenu"] for n in a["noeuds"]))
        self.assertEqual(len(a["noeuds"]), a["comptes"]["total"])

    def test_consomme_ne_depasse_pas_le_budget(self):
        a = self.arbre(budget=120)
        self.assertLessEqual(a["consomme"], 120)

    def test_les_retenus_sont_les_mieux_classes(self):
        a = self.arbre(budget=120)
        scores_retenus = [n["score"] for n in a["noeuds"] if n["retenu"]]
        scores_ecartes = [n["score"] for n in a["noeuds"] if not n["retenu"]]
        if scores_retenus and scores_ecartes:
            self.assertGreaterEqual(min(scores_retenus), 0.0)
            self.assertGreaterEqual(max(scores_retenus), max(scores_ecartes))


class Contexte(ArbreBase):
    def test_la_carte_cite_tous_les_noeuds(self):
        a = self.arbre()
        c = contexte.carte(a["noeuds"])
        for n in a["noeuds"]:
            self.assertIn(Path(n["chemin"]).stem, c)

    def test_la_carte_marque_les_non_joints(self):
        a = self.arbre(budget=60)
        self.assertIn("(non joint)", contexte.carte(a["noeuds"]))

    def test_assembler_ne_joint_que_les_retenus(self):
        a = self.arbre()
        choisi = a["retenus"][:1]
        texte, detail = contexte.assembler(a, choisi)
        self.assertEqual(len(detail), 1)
        self.assertIn("Carte des notes", texte)

    def test_note_longue_tronquee_et_signalee(self):
        ecrire("Longue.md", "# Longue\n\n" + ("calibration " * 3000))
        self.idx = fresh_index(VAULT)
        self.idx.refresh()
        a = parcours.construire(self.idx, "calibration",
                                depart=str(VAULT / "Longue.md"), budget=200_000)
        texte, detail = contexte.assembler(a)
        longue = [d for d in detail if d["nom"] == "Longue.md"]
        self.assertTrue(longue and longue[0]["tronquee"])
        self.assertLessEqual(longue[0]["caracteres"], parcours.MAX_PAR_NOTE)
        self.assertIn("note tronquée", texte)


class Mesure(ArbreBase):
    """La decision 0029 exigeait de mesurer. Ces tests figent ce que la mesure a dit."""

    def vault_realiste(self):
        """48 notes en six grappes : dense a l'interieur, rare entre grappes.

        Le tirage est **seede** : la mesure doit etre reproductible, sinon les chiffres
        du test ne veulent rien dire. Et les liens doivent sortir de l'ensemble des
        amorces — un premier essai ou chaque note citait ses deux premiers freres donnait
        huit amorces formant une clique fermee, donc zero propagation : l'arbre paraissait
        econome parce qu'il ne trouvait rien.
        """
        import random
        effacer(VAULT.rglob("*.md"))
        corps = ("La prevision demande une discipline de mesure : hypothese, probabilite, "
                 "puis releve du resultat. " * 12)
        noms = ["%s-%02d" % (g, i)
                for g in ("Calibration", "Lecture", "Projet", "Sante", "Finance", "Cuisine")
                for i in range(8)]
        tirage = random.Random(7)
        for nom in noms:
            g = nom.rsplit("-", 1)[0]
            liens = tirage.sample([n for n in noms if n.startswith(g) and n != nom], 2)
            if tirage.random() < 0.25:                  # pont rare vers une autre grappe
                liens.append(tirage.choice([n for n in noms if not n.startswith(g)]))
            ecrire(nom + ".md", "# %s\n\n%s\n\n%s\n"
                   % (nom, corps, " ".join("[[%s]]" % f for f in liens)))
        self.idx = fresh_index(VAULT)
        self.idx.refresh()
        return noms

    def test_l_economie_vient_du_plafond_pas_de_l_arbre(self):
        """Le resultat inconfortable, garde exprès.

        Contre la recherche plate NON BORNEE, l'arbre parait tres econome (ici ~10 000
        caracteres de moins). Mais c'est le seul effet du budget : compare a la MEME
        recherche plate tronquee au meme budget, l'ecart tombe a quelques pour cent, dans
        un sens ou dans l'autre selon la forme du vault.

        Autrement dit : l'arbre ne fait pas economiser de jetons, le plafond les economise.
        Si un jour ce test casse parce que l'ecart a budget egal devient large, ce sera
        une anomalie a comprendre, pas une amelioration a celebrer.
        """
        self.vault_realiste()
        q = "prevision probabilite mesure"
        a = parcours.construire(self.idx, q)
        c = contexte.comparer(self.idx, q, a)
        self.assertGreater(c["plat_caracteres"], c["arbre_caracteres"],
                           "sans plafond, la recherche plate doit couter plus")
        ecart = abs(c["gain_a_budget_egal"]) / max(1, c["plat_tronque_caracteres"])
        self.assertLess(ecart, 0.15,
                        "a budget egal l'arbre coute a peu pres le meme prix (ecart %.0f%%) : "
                        "l'economie vient du plafond, pas de l'arbre" % (ecart * 100))

    def test_ce_que_l_arbre_apporte_vraiment(self):
        """La contrepartie des caracteres en plus : des notes que le score n'avait pas."""
        self.vault_realiste()
        q = "prevision probabilite mesure"
        a = parcours.construire(self.idx, q)
        c = contexte.comparer(self.idx, q, a)
        self.assertGreater(c["apport_liens"], 0,
                           "sans apport par les liens, l'arbre ne sert a rien")
        par_lien = sum(1 for n in a["noeuds"] if n["retenu"] and n["niveau"] > 0)
        self.assertGreater(par_lien, 0)

    def test_la_carte_est_comptee(self):
        self.vault_realiste()
        q = "prevision probabilite mesure"
        a = parcours.construire(self.idx, q)
        c = contexte.comparer(self.idx, q, a)
        self.assertGreater(c["carte_caracteres"], 0)
        self.assertLess(c["carte_caracteres"], c["arbre_caracteres"])


class Routes(ArbreBase):
    def setUp(self):
        super().setUp()
        self.c = create_app(with_plugins=False).test_client()
        self.h = {"X-Prisme-Token": security.TOKEN}
        DEHORS.mkdir(parents=True, exist_ok=True)
        (DEHORS / "Prive.md").write_text("# Prive\n\nsecret-hors-vault\n", encoding="utf-8")

    def post(self, url, corps):
        return self.c.post(url, json=corps, headers=self.h)

    def test_construire_sans_question_ni_depart(self):
        r = self.post("/api/arbre/construire", {})
        self.assertEqual(r.status_code, 400)

    def test_construire_rend_l_arbre(self):
        r = self.post("/api/arbre/construire", {"question": "calibration Brier"})
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertTrue(d["noeuds"])
        self.assertIn("retenus", d)
        self.assertIn("comptes", d)

    def test_construire_n_appelle_pas_le_modele(self):
        """Point central de 0029 : on voit l'arbre AVANT que l'IA parle.

        La configuration pointe vers 127.0.0.1:9, qui ne repond pas. Si la route appelait
        le modele, elle mettrait un temps fou ou renverrait une erreur de service.
        """
        r = self.post("/api/arbre/construire", {"question": "calibration"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("reponse", r.get_json())

    def test_depart_hors_vault_refuse(self):
        r = self.post("/api/arbre/construire", {"depart": str(DEHORS / "Prive.md")})
        self.assertEqual(r.status_code, 403)

    def test_retenus_forges_refuses(self):
        """La liste « retenus » revient du navigateur et sert a lire des fichiers.

        Un chemin qui ne figure pas dans l'arbre construit n'est jamais lu, meme s'il
        est dans le vault : sinon la route devient un lecteur de fichiers arbitraire.
        """
        a = self.post("/api/arbre/construire", {"question": "calibration"}).get_json()
        r = self.post("/api/arbre/repondre",
                      {"question": "q", "arbre": a, "retenus": [str(DEHORS / "Prive.md")]})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Aucune note retenue", r.get_json()["error"])

    def test_repondre_sans_arbre(self):
        r = self.post("/api/arbre/repondre", {"question": "q"})
        self.assertEqual(r.status_code, 400)

    def test_profondeur_plafonnee(self):
        r = self.post("/api/arbre/construire", {"question": "calibration", "profondeur": 99})
        self.assertEqual(r.get_json()["profondeur"], 4)

    def test_budget_plafonne(self):
        r = self.post("/api/arbre/construire", {"question": "calibration", "budget": 10 ** 9})
        self.assertEqual(r.get_json()["budget"], 200_000)

    def test_comparaison_sur_demande_seulement(self):
        sans = self.post("/api/arbre/construire", {"question": "calibration"}).get_json()
        self.assertNotIn("comparaison", sans)
        avec = self.post("/api/arbre/construire",
                         {"question": "calibration", "comparer": True}).get_json()
        self.assertIn("comparaison", avec)


class Interface(unittest.TestCase):
    """Le cablage de la page : une route sans bouton n'existe pas pour l'auteur."""

    def setUp(self):
        from prisme_core.paths import WEB_DIR
        self.html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
        self.js = (WEB_DIR / "js" / "arbre.js").read_text(encoding="utf-8")
        self.css = (WEB_DIR / "css" / "arbre.css").read_text(encoding="utf-8")

    def test_la_case_a_cocher_garde_sa_largeur(self):
        """core.css met `width:100%` sur les `input` : sans contre-ordre, la case a
        cocher occupait toute la ligne et poussait le nom, le motif et le cout hors du
        cadre. La liste n'affichait plus que des cases flottantes. Vu au navigateur,
        invisible aux tests — d'ou ce garde-fou grossier mais utile.
        """
        self.assertIn('input[type="checkbox"]', self.css)
        bloc = self.css.split('input[type="checkbox"]')[-1][:160]
        self.assertIn("width", bloc)

    def test_bouton_dans_la_barre(self):
        self.assertIn("openArbre()", self.html)

    def test_fenetre_et_script_charges(self):
        self.assertIn('id="marbre"', self.html)
        self.assertIn("/static/js/arbre.js", self.html)
        self.assertIn("/static/css/arbre.css", self.html)

    def test_repondre_desactive_tant_que_rien_n_est_coche(self):
        self.assertIn('id="arb-repondre"', self.html)
        self.assertIn("disabled", self.html.split('id="arb-repondre"')[1][:200])

    def test_l_elagage_recalcule_le_budget(self):
        self.assertIn("arbMajBudget", self.js)
        self.assertIn("arbBasculer", self.js)


if __name__ == "__main__":
    unittest.main()
