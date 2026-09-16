# -*- mode: python ; coding: utf-8 -*-
# Construction : pyinstaller packaging/PRISME.spec  (depuis la racine du depot)
# Resultat     : dist/PRISME.exe, un seul fichier. Le dossier plugins/ se pose a cote.
import os
from PyInstaller.utils.hooks import collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

# Modules de la bibliotheque standard utilises par les plugins distribues a part :
# ils doivent etre dans l'exe puisque les plugins n'embarquent que du Python pur.
STDLIB_FOR_PLUGINS = [
    "xml", "concurrent", "urllib", "http", "email", "json", "ipaddress",
    "sysconfig", "subprocess", "socket", "tempfile", "hashlib", "importlib",
]
hidden = collect_submodules("prisme_core") + ["requests"]
for mod in STDLIB_FOR_PLUGINS:
    hidden += collect_submodules(mod)

a = Analysis(
    [os.path.join(ROOT, "prisme.py")],
    pathex=[ROOT],
    datas=[(os.path.join(ROOT, "prisme_core", "web"), os.path.join("prisme_core", "web"))],
    hiddenimports=hidden,
    excludes=["tkinter"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="PRISME",
    console=True,
    upx=False,
)
