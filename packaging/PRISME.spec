# -*- mode: python ; coding: utf-8 -*-
# Distribution en dossier : PRISME.exe + _internal/ ; plugins copiés séparément.
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_dynamic_libs, collect_data_files, copy_metadata

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
hidden = collect_submodules("prisme_core") + ["requests", "onnxruntime", "tokenizers"]
# Les plugins externes sont importés après compilation : leurs imports sont explicites ici.
for mod in ("xml", "concurrent", "urllib", "http", "email", "json", "ipaddress",
            "sysconfig", "subprocess", "socket", "tempfile", "hashlib", "importlib",
            "ctypes", "sqlite3", "statistics", "ddgs", "tokenizers"):
    hidden += collect_submodules(mod)
datas = [(os.path.join(ROOT, "prisme_core", "web"), "prisme_core/web")]
for mod in ("onnxruntime", "tokenizers", "ddgs"):
    datas += collect_data_files(mod)
    datas += copy_metadata(mod)
binaries = collect_dynamic_libs("onnxruntime")
a = Analysis([os.path.join(ROOT, "prisme.py")], pathex=[ROOT],
             datas=datas, binaries=binaries, hiddenimports=hidden,
             excludes=["tkinter", "onnx", "torch", "tensorflow"])
# Le code des plugins doit rester exclusivement dans plugins/.
for nom, chemin, _ in a.pure:
    # Le dépôt et Python peuvent se trouver sur deux lecteurs Windows différents.
    if Path(chemin).resolve().is_relative_to(Path(ROOT) / "plugins"):
        raise RuntimeError("Plugin embarqué par erreur : " + nom)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name="PRISME", console=True, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="PRISME", upx=False)
