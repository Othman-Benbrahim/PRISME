"""Assemblage de l'application Flask et lancement."""
import threading
import webbrowser

from flask import Flask, jsonify

from . import NAME, __version__, plugins, secrets
from .config import rd_cfg
from .envfile import load_env_file
from .paths import HOME, WEB_DIR, import_legacy_config
from .plugin_install import MAX_ZIP
from .routes import ai, engram, files, pages, plugin_manager, search, security, setup

HOST = "127.0.0.1"
PORT = 5000


def create_app(with_plugins=True):
    app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = MAX_ZIP + 1024 * 1024
    for module in (security, pages, setup, ai, files, search, plugin_manager, engram):
        app.register_blueprint(module.bp)
    app.register_blueprint(plugins.bp)

    # Un chemin refuse par la garde du vault devient une reponse JSON propre
    @app.errorhandler(PermissionError)
    def _forbidden(e):
        return jsonify({"error": str(e) or "Accès refusé"}), 403

    @app.errorhandler(FileNotFoundError)
    def _missing(e):
        return jsonify({"error": "Fichier ou dossier introuvable"}), 404

    if with_plugins:
        plugins.load_all()
    return app


def main():
    print(f"\n  {NAME} {__version__}\n  http://localhost:{PORT}  (Ctrl+C pour arreter)\n")
    if import_legacy_config():
        print("-> Configuration de Second Brain V1 reprise dans le profil PRISME")
    state = rd_cfg().get("key_state")
    if not secrets.available():
        print("-> ATTENTION : chiffrement indisponible sur ce systeme, les cles restent en clair")
    elif state == "illisible":
        print("-> Cle d'API illisible sur cette machine : ressaisissez-la dans Parametres")
    load_env_file(HOME / ".env")          # .env racine, avant tout plugin
    print("-> Chargement des plugins...")
    app = create_app()
    print(f"-> {len(plugins.active_plugins())} plugin(s) actif(s)")
    try:
        from .index import get_index
        idx = get_index()
        idx.start_background()
        print(f"-> Index : {idx.db_path} ({'FTS5' if idx.fts else 'sans FTS5, recherche simple'})\n")
    except Exception as e:                                   # noqa: BLE001
        print(f"-> Index indisponible : {e}\n")
    threading.Timer(1.6, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
