"""Contrôles de la distribution réelle, dans le profil isolé créé par le lanceur."""
import json
from pathlib import Path
import sys

# Inventaire des plugins de la distribution. Il double celui de `tests/test_e1_plugins.py`,
# et lui seul est exerce par le binaire gele : un plugin ajoute sans etre inscrit ici passe
# toute la suite de tests et fait echouer la construction. `test_e9_distribution.py` les lie
# desormais au contenu reel de `plugins/`.
ATTENDUS = {"arxiv", "calibration", "constat", "context", "duckduckgo",
            "embeddings-locaux", "nexus-arche", "osint-cx", "prompts", "rss"}


def exiger(condition, message):
    if not condition:
        raise RuntimeError(message)


def verifier(rapport, modele, sans_plugins=False):
    from . import plugins, secrets
    from .paths import DATA_DIR, PLUGINS_DIR
    from .app import create_app
    if sans_plugins:
        exiger(not PLUGINS_DIR.exists(), "Le dossier plugins doit être physiquement absent")
    from .config import wr_cfg
    wr_cfg({"workspace": str(DATA_DIR / "vault"), "workspaces": []})
    client = create_app().test_client()
    etats = {ident: p.status for ident, p in plugins.REGISTRY.items()}
    exiger(set(etats) == (set() if sans_plugins else ATTENDUS), f"Plugins inattendus : {etats}")
    exiger(all(s == "actif" for s in etats.values()), f"Plugin inactif : {etats}")
    jeton = client.get("/api/token").get_json()["token"]
    entetes = {"X-Prisme-Token": jeton}
    exiger(client.get("/api/config").status_code == 403, "Garde de session inactive")
    exiger(client.get("/").status_code == 200, "Interface inaccessible")
    rep = client.post("/api/setup", headers=entetes, json={"workspace": str(DATA_DIR / "vault")})
    exiger(rep.status_code == 200, f"Initialisation impossible : {rep.get_json()}")
    for chemin in ("/api/setup/state", "/api/plugin-manager/list"):
        exiger(client.get(chemin, headers=entetes).status_code == 200, chemin)
    for ident, plugin in plugins.REGISTRY.items():
        for nom in ("ui.js", "ui.css"):
            if (PLUGINS_DIR / ident / nom).is_file():
                exiger(client.get(f"/plugins/{ident}/{nom}").status_code == 200, f"Asset absent : {ident}/{nom}")
    resultat = {"ok": True, "plugins": etats, "sans_plugins": sans_plugins,
                "executable": sys.executable, "gele": bool(getattr(sys, "frozen", False))}
    if sys.platform == "win32":
        valeur = secrets.protect("contrôle E9")
        exiger(valeur.startswith("dpapi:"), "DPAPI indisponible")
        exiger(secrets.reveal(valeur)[0] == "contrôle E9", "DPAPI : relecture impossible")
        resultat["dpapi"] = True
    if not sans_plugins:
        exiger(modele is not None, "Modèle de contrôle manquant")
        import numpy as np
        from ddgs import DDGS
        moteur_module = sys.modules["prisme_plugins.embeddings_locaux.moteur"]
        vecteurs = np.asarray(moteur_module.Moteur(Path(modele)).encoder(
            ["prediction horizon calibrer", "anticiper prospective prevoir", "oignon cuisine recette"]))
        exiger(vecteurs.shape == (3, 16), f"Dimension incorrecte : {vecteurs.shape}")
        exiger(np.all(np.isfinite(vecteurs)), "Vecteurs non finis")
        exiger(np.allclose(np.linalg.norm(vecteurs, axis=1), 1, atol=1e-5), "Normalisation incorrecte")
        proche, loin = float(vecteurs[0] @ vecteurs[1]), float(vecteurs[0] @ vecteurs[2])
        exiger(proche > loin, "Le classement sémantique du modèle de contrôle est inversé")
        resultat["onnx"] = {"dimension": 16, "proche": proche, "loin": loin}
        moteurs_web = DDGS()._get_engines("text", "duckduckgo")
        exiger(bool(moteurs_web), "Moteur DDGS absent de la distribution")
        resultat["ddgs"] = [type(m).__name__ for m in moteurs_web]
    from .index import forget_all
    forget_all()
    rapport.parent.mkdir(parents=True, exist_ok=True)
    rapport.write_text(json.dumps(resultat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Diagnostic réussi :", rapport)
