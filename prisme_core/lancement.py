"""Choisit le mode de lancement avant de charger le profil ou Flask."""
import argparse
import os
from pathlib import Path
import runpy
import sys
import tempfile


def main():
    for flux in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="PRISME — mémoire locale")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--mcp", action="store_true", help="adaptateur MCP sur l'entrée standard")
    modes.add_argument("--verifier-distribution", type=Path, metavar="RAPPORT_JSON",
                       help="diagnostic hors réseau dans un profil temporaire")
    parser.add_argument("--modele-test", type=Path, help="modèle ONNX de contrôle (construction)")
    parser.add_argument("--sans-plugins", action="store_true", help="attendre un dossier plugins absent lors du diagnostic")
    parser.add_argument("--sans-navigateur", action="store_true")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("le port doit être compris entre 1 et 65535")
    if (args.modele_test or args.sans_plugins) and not args.verifier_distribution:
        parser.error("--modele-test et --sans-plugins sont réservés au diagnostic")
    if args.mcp:
        racine = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
        runpy.run_path(str(racine / "mcp" / "prisme_mcp.py"), run_name="__main__")
        return
    if args.verifier_distribution:
        # Aucun import des chemins, de la configuration ou de Flask avant cet isolement.
        with tempfile.TemporaryDirectory(prefix="prisme-diagnostic-") as dossier:
            os.environ["PRISME_DATA_DIR"] = dossier
            os.environ.pop("PRISME_NO_AUTH", None)
            from .diagnostic_distribution import verifier
            verifier(args.verifier_distribution.resolve(), args.modele_test, args.sans_plugins)
        return
    from .app import main as lancer
    lancer(port=args.port, ouvrir_navigateur=not args.sans_navigateur)
