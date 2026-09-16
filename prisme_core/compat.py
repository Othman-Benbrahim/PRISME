"""Passerelle TEMPORAIRE pour les plugins herites de Second Brain V1.

Les plugins V1 font `from second_brain import _ai_call, ...`. Ce module
enregistre un faux module `second_brain` qui expose uniquement ces noms.
Il disparait a l'etape E1, remplace par prisme_core.api.
"""
import sys
import types

from .markdown import extract_link_refs, resolve_ref
from .providers import _ai_call

EXPOSED = {
    "_ai_call": _ai_call,
    "extract_link_refs": extract_link_refs,
    "resolve_ref": resolve_ref,
}


def install():
    if "second_brain" in sys.modules:
        return sys.modules["second_brain"]
    mod = types.ModuleType("second_brain")
    mod.__doc__ = "Passerelle de compatibilite V1 (temporaire, retiree en E1)."
    for name, obj in EXPOSED.items():
        setattr(mod, name, obj)
    sys.modules["second_brain"] = mod
    return mod
