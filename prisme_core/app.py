"""Assemblage de l'application Flask et lancement."""
import threading
import webbrowser

from flask import Flask

from . import NAME, __version__
from .config import rd_cfg
from .envfile import load_env_file
from .paths import HOME, WEB_DIR, import_legacy_config
from .plugins import LOADED_PLUGINS, bp as plugin_assets_bp, load_plugins
from .routes import ai, files, pages, search, security, setup

HOST = "127.0.0.1"
PORT = 5000


def create_app(with_plugins=True):
    app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="/static")
    for module in (security, pages, setup, ai, files, search):
        app.register_blueprint(module.bp)
    app.register_blueprint(plugin_assets_bp)
    if with_plugins:
        load_plugins(app, rd_cfg)
    return app


def main():
    print(f"\n  {NAME} {__version__}\n  http://localhost:{PORT}  (Ctrl+C pour arreter)\n")
    if import_legacy_config():
        print("-> Configuration de Second Brain V1 reprise dans le profil PRISME")
    load_env_file(HOME / ".env")          # .env racine, avant tout plugin
    print("-> Chargement des plugins...")
    app = create_app()
    print(f"-> {len(LOADED_PLUGINS)} plugin(s) actif(s)\n")
    threading.Timer(1.6, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    app.run(host=HOST, port=PORT, debug=False)
