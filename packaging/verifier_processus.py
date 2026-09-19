"""Vérifie HTTP et MCP via de vrais processus du binaire, hors de son dossier."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


def verifier(executable, travail):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    adresse = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["PRISME_DATA_DIR"] = str(travail / "profil-http")
    env.pop("PRISME_NO_AUTH", None)
    profil = Path(env["PRISME_DATA_DIR"])
    profil.mkdir(parents=True, exist_ok=True)
    (profil / "config.json").write_text(json.dumps({"workspace": str(travail / "vault-http"), "workspaces": []}), encoding="utf-8")
    def requete(chemin, donnees=None, jeton=None):
        h = {"Content-Type": "application/json"}
        if jeton:
            h["X-Prisme-Token"] = jeton
        r = Request(adresse + chemin, data=json.dumps(donnees).encode() if donnees is not None else None, headers=h)
        with urlopen(r, timeout=3) as reponse:
            return reponse.read()
    with (travail / "serveur.log").open("wb") as log:
        p = subprocess.Popen([str(executable), "--sans-navigateur", "--port", str(port)], cwd=travail, env=env, stdout=log, stderr=log)
        try:
            for _ in range(100):
                if p.poll() is not None:
                    raise RuntimeError((travail / "serveur.log").read_text(encoding="utf-8", errors="replace"))
                try:
                    jeton = json.loads(requete("/api/token"))["token"]
                    break
                except (URLError, TimeoutError, ConnectionError):
                    time.sleep(0.2)
            else:
                raise RuntimeError("Serveur non disponible après 20 secondes")
            if b"<html" not in requete("/").lower():
                raise RuntimeError("Page HTML absente")
            requete("/api/setup", {"workspace": str(travail / "vault-http")}, jeton)
            config = json.loads(requete("/api/agents/mcp", {"nom": "Contrôle E9"}, jeton))["configuration"]["mcpServers"]["prisme"]
            if Path(config["command"]).resolve() != executable.resolve() or config["args"] != ["--mcp"]:
                raise RuntimeError("La configuration MCP du binaire demande encore Python")
            mcp_env = {**env, **config["env"]}
            messages = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "E9", "version": "1"}}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            ]
            reponse = subprocess.run([config["command"], *config["args"]], input="".join(json.dumps(x) + "\n" for x in messages),
                                     text=True, encoding="utf-8", capture_output=True, cwd=travail, env=mcp_env, timeout=15, check=True)
            lignes = [json.loads(x) for x in reponse.stdout.splitlines() if x.strip()]
            if len(lignes) != 2 or any("error" in x for x in lignes) or not lignes[1]["result"]["tools"]:
                raise RuntimeError("Protocole MCP invalide : " + reponse.stdout)
        finally:
            p.terminate()
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=10)
    print("HTTP et MCP du binaire : OK")


if __name__ == "__main__":
    verifier(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
