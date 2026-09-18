"""Dialogues dans l'interface : plus aucun popup du navigateur."""
import re
import unittest

from commun import ROOT, reset_vault

from prisme_core.app import create_app

WEB = ROOT / "prisme_core" / "web"
POPUP = re.compile(r"(?<![\w.])(alert|confirm|prompt)\s*\(")


class TestDialogues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reset_vault()
        cls.client = create_app(with_plugins=False).test_client()

    def test_fichiers_servis_et_branches(self):
        with self.client.get("/static/js/dialogues.js") as r:
            self.assertEqual(r.status_code, 200)
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('id="mdialog"', html)
        self.assertIn("/static/js/dialogues.js", html)
        # dialogues.js doit être chargé avant ceux qui l'utilisent
        self.assertLess(html.index("/static/js/dialogues.js"), html.index("/static/js/explorer.js"))

    def test_plus_aucun_popup_du_navigateur(self):
        fautifs = []
        for f in sorted(list((WEB / "js").glob("*.js")) + list((ROOT / "plugins").glob("*/ui.js"))):
            for num, ligne in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                sans_commentaire = ligne.split("//")[0]
                if POPUP.search(sans_commentaire) and "confirmer(" not in sans_commentaire:
                    fautifs.append(f"{f.name}:{num} {ligne.strip()[:70]}")
        self.assertEqual(fautifs, [], "utiliser confirmer() / demanderTexte() : " + " ; ".join(fautifs))


if __name__ == "__main__":
    unittest.main()
