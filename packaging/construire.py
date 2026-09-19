"""Construit, contrôle puis archive une distribution à partir des fichiers suivis."""
import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUS = {"tests", "node_modules", "__pycache__", ".git", ".env"}
DOSSIERS = {"plugins", "guides-plugins", "mcp", "docs"}
FICHIERS = {"README.md", "LICENSE", "PLUGIN-DEVELOPMENT.md"}


def executer(args, **options):
    print("+", " ".join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **options)


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True, encoding="utf-8").strip()


def livrable(nom):
    p = Path(nom)
    return (p.parts[0] in DOSSIERS or nom in FICHIERS) and not (
        set(p.parts) & EXCLUS or p.suffix in {".pyc", ".bak"} or p.name.startswith(".env"))


def copier_fichiers(destination):
    # Ne copie jamais un fichier local non suivi (secrets, cache, modèles téléchargés).
    for nom in git("ls-files", "-z").split("\0"):
        if nom and livrable(nom):
            origine = ROOT / nom
            if origine.is_symlink():
                raise RuntimeError("Lien symbolique non pris en charge : " + nom)
            cible = destination / nom
            cible.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origine, cible)


def empreinte(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


def licences(destination):
    versions = {}
    for dist in metadata.distributions():
        nom = dist.metadata["Name"]
        versions[nom] = dist.version
        for entree in dist.files or ():
            p = Path(str(entree))
            if any(x.lower().startswith(("license", "licence", "copying", "notice")) for x in p.parts):
                source = Path(dist.locate_file(entree))
                if source.is_file() and not source.is_symlink():
                    # Aplatir le chemin, sans accepter de traversée issue de métadonnées.
                    cible = destination / "licences" / nom / "_".join(p.parts)
                    cible.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, cible)
    return dict(sorted(versions.items()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sortie", type=Path, required=True, help="dossier neuf, créé par ce script")
    parser.add_argument("--controle-linux", action="store_true", help="contrôle développeur, ne produit pas une release Windows")
    args = parser.parse_args()
    if not args.controle_linux and (sys.platform != "win32" or platform.machine().lower() not in {"amd64", "x86_64"}):
        parser.error("la release Windows x64 doit être construite sous Windows x64")
    sortie = args.sortie.resolve()
    if sortie.exists():
        parser.error("le dossier de sortie existe déjà ; choisissez un nouveau nom")
    if git("status", "--porcelain", "--untracked-files=no"):
        parser.error("les modifications suivies doivent être commitées avant construction")
    commit = git("rev-parse", "HEAD")
    sortie.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="prisme-build-") as temporaire:
        travail = Path(temporaire)
        executer([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                  "--distpath", sortie, "--workpath", travail / "pyinstaller", ROOT / "packaging/PRISME.spec"], cwd=ROOT)
        application = sortie / "PRISME"
        copier_fichiers(application)
        versions = licences(application)
        modele = travail / "modele-controle"
        executer([sys.executable, ROOT / "tests/fixtures/modele_minuscule.py", modele])
        executable = application / ("PRISME.exe" if sys.platform == "win32" else "PRISME")
        env = os.environ.copy()
        env.pop("PRISME_NO_AUTH", None)
        env.pop("PYTHONPATH", None)
        env["PRISME_DATA_DIR"] = str(travail / "profil")
        # Les tests du binaire ne peuvent pas retrouver Python/Node dans PATH.
        env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32") if sys.platform == "win32" else "/usr/bin:/bin"
        executer([executable, "--verifier-distribution", sortie / "avec-plugins.json", "--modele-test", modele],
                  cwd=travail, env=env, timeout=120)
        cache_plugins = travail / "plugins-retires"
        shutil.move(str(application / "plugins"), cache_plugins)
        try:
            executer([executable, "--verifier-distribution", sortie / "sans-plugins.json", "--sans-plugins"],
                      cwd=travail, env=env, timeout=120)
        finally:
            shutil.move(str(cache_plugins), application / "plugins")
        executer([sys.executable, ROOT / "packaging/verifier_processus.py", executable, travail], env=env, timeout=90)
        rapport = {"commit": commit, "plateforme": platform.platform(), "python": platform.python_version(),
                   "release_windows": sys.platform == "win32", "dependances_construction": versions,
                   "controles": ["neuf plugins actifs", "sans dossier plugins", "inférence ONNX", "HTTP", "MCP"],
                   "limites": ["inspection visuelle manuelle requise", "services réseau non testés par ce build"]}
        (application / "construction.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for nom in ("avec-plugins.json", "sans-plugins.json"):
            shutil.copy2(sortie / nom, application / nom)
        hashes = {p.relative_to(application).as_posix(): empreinte(p) for p in sorted(application.rglob("*")) if p.is_file()}
        (application / "empreintes.json").write_text(json.dumps(hashes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        etiquette = "Windows-x64" if sys.platform == "win32" else "CONTROLE-Linux"
        archive = sortie / f"PRISME-{etiquette}-{commit[:12]}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for fichier in sorted(application.rglob("*")):
                if fichier.is_file():
                    z.write(fichier, "PRISME/" + fichier.relative_to(application).as_posix())
        sources = sortie / f"PRISME-sources-{commit[:12]}.zip"
        executer(["git", "-C", ROOT, "archive", "--format=zip", f"--output={sources}", commit])
        (sortie / "SHA256SUMS.txt").write_text("".join(f"{empreinte(p)}  {p.name}\n" for p in (archive, sources)), encoding="utf-8")
    print("Distribution contrôlée :", archive)
    print("La publication attend la vérification visuelle Windows.")


if __name__ == "__main__":
    main()
