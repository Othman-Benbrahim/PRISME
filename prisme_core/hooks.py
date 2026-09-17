"""Hooks synchrones des plugins (docs/decisions/0009).

emit() appelle chaque abonne l'un apres l'autre, avant que l'operation soit
confirmee. Chaque appel a un delai maximal : au-dela, PRISME n'attend plus et
le signale. Python ne sait pas interrompre un fil d'execution : un hook
abandonne continue en arriere-plan jusqu'a sa fin, sans bloquer l'interface.
"""
import threading
import time
import traceback

EVENTS = ("note_saved", "note_created", "note_renamed", "note_deleted")
TIMEOUT = 3.0

_SUBSCRIBERS = {event: [] for event in EVENTS}   # event -> [(plugin_id, fn)]
_LOCK = threading.Lock()
_is_active = lambda plugin_id: True              # remplace par le registre des plugins


def set_activity_check(fn):
    global _is_active
    _is_active = fn


def subscribe(plugin_id, event, fn):
    if event not in _SUBSCRIBERS:
        raise ValueError(f"Evenement inconnu : {event} (connus : {', '.join(EVENTS)})")
    with _LOCK:
        _SUBSCRIBERS[event].append((plugin_id, fn))


def unsubscribe_plugin(plugin_id):
    with _LOCK:
        for event in _SUBSCRIBERS:
            _SUBSCRIBERS[event] = [s for s in _SUBSCRIBERS[event] if s[0] != plugin_id]


def emit(event, **payload):
    """Renvoie la liste des incidents : [{plugin, event, probleme, detail}]."""
    with _LOCK:
        subscribers = list(_SUBSCRIBERS.get(event, ()))
    incidents = []
    for plugin_id, fn in subscribers:
        if not _is_active(plugin_id) or payload.get("origin") == plugin_id:
            continue                                     # pas de boucle sur ses propres ecritures
        box = {}

        def run(fn=fn, box=box):
            try:
                fn(**payload)
            except Exception as e:                       # noqa: BLE001 - on isole le plugin
                box["error"] = f"{type(e).__name__}: {e}"
                box["trace"] = traceback.format_exc(limit=4)

        started = time.monotonic()
        worker = threading.Thread(target=run, name=f"hook-{plugin_id}-{event}", daemon=True)
        worker.start()
        worker.join(TIMEOUT)
        if worker.is_alive():
            incidents.append({"plugin": plugin_id, "event": event, "probleme": "delai",
                              "detail": f"abandonne apres {TIMEOUT:.0f} s"})
            print(f"  ! Hook {plugin_id}/{event} : delai de {TIMEOUT:.0f} s depasse")
        elif "error" in box:
            incidents.append({"plugin": plugin_id, "event": event, "probleme": "erreur",
                              "detail": box["error"]})
            print(f"  x Hook {plugin_id}/{event} : {box['error']}\n{box['trace']}")
        else:
            elapsed = time.monotonic() - started
            if elapsed > 1.0:
                print(f"  ! Hook {plugin_id}/{event} lent : {elapsed:.1f} s")
    return incidents
