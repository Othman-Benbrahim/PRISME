"""Confort d'édition : gouttière, historique, recherche dans la note.

Le comportement lui-même se vérifie dans un navigateur ; ces tests garantissent
que les fichiers sont bien servis et branchés dans la page.
"""
import unittest

from commun import ROOT, reset_vault

from prisme_core.app import create_app
from prisme_core.routes import security

FICHIERS = ["/static/js/gutter.js", "/static/js/history.js", "/static/js/find-in-note.js",
            "/static/css/editeur.css"]


class TestConfortEditeur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reset_vault()
        cls.client = create_app(with_plugins=False).test_client()

    def test_fichiers_servis(self):
        for url in FICHIERS:
            with self.client.get(url) as r:
                self.assertEqual(r.status_code, 200, url)

    def test_page_branchee(self):
        html = self.client.get("/").get_data(as_text=True)
        for marqueur in ('id="md-gutter"', 'id="find-bar"', 'id="btn-undo"', 'id="btn-redo"',
                         'id="ed-status"', 'id="ed-edit-pane"'):
            self.assertIn(marqueur, html, marqueur)
        for url in FICHIERS:
            self.assertIn(url, html, url)
        # l'ordre compte : gutter.js avant history.js (scrollEditorTo) et find-in-note.js
        self.assertLess(html.index("/static/js/gutter.js"), html.index("/static/js/history.js"))
        self.assertLess(html.index("/static/js/gutter.js"), html.index("/static/js/find-in-note.js"))
        self.assertLess(html.index("/static/js/editor.js"), html.index("/static/js/gutter.js"))

    def test_fichiers_courts(self):
        web = ROOT / "prisme_core" / "web"
        for f in list((web / "js").glob("*.js")) + list((web / "css").glob("*.css")):
            self.assertLess(f.stat().st_size, 20_000, f.name)


if __name__ == "__main__":
    unittest.main()
