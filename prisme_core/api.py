"""API publique des plugins PRISME — version 1.

C'est le SEUL module qu'un plugin doit importer depuis le coeur. Tout le reste
de prisme_core est interne et peut changer sans preavis.

Un plugin expose :

    def register(ctx):          # ctx : PluginContext
        @ctx.route("/recherche", methods=["POST"])
        def recherche():
            ...

Ses routes sont servies sous /api/plugins/<id>/ . Voir PLUGIN-DEVELOPMENT.md.
"""
import os
import shutil
from pathlib import Path

from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException
from flask import jsonify, request

from . import hooks, secrets
from .frontmatter import update as update_frontmatter
from .config import rd_cfg
from .markdown import extract_link_refs, extract_tags, resolve_ref   # reexportes (voir __all__)
from .paths import DATA_DIR, LEGACY_DATA_DIR
from .providers import _ai_call, needs_key
from .vault import iter_md, safe_path, snapshot, vault_root
from .vecteurs.contrat import Fournisseur as EmbeddingProvider          # reexporte
from .vecteurs.contrat import VecteurIndisponible as EmbeddingUnavailable

__all__ = [
    "API_VERSION", "EVENTS", "PERMISSIONS", "PluginContext", "PluginPermissionError",
    "extract_link_refs", "extract_tags", "resolve_ref",
    "EmbeddingProvider", "EmbeddingUnavailable", "update_frontmatter",
]

API_VERSION = 1
EVENTS = hooks.EVENTS

PERMISSIONS = {
    "network": "Acceder a Internet",
    "vault_write": "Creer et modifier des notes du vault",
    "secrets": "Lire des secrets (cles d'API) enregistres pour ce plugin",
    "processes": "Lancer des programmes installes sur la machine",
}

_ALL_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


class PluginPermissionError(PermissionError):
    pass


class PluginContext:
    """Ce qu'un plugin recoit dans register(ctx)."""

    def __init__(self, plugin_id, name, directory, manifest):
        self.id = plugin_id
        self.name = name
        self.directory = Path(directory)
        self.manifest = manifest
        self.permissions = frozenset(manifest.get("permissions", []))
        self._declared_secrets = {s["name"] for s in manifest.get("secrets", [])}
        self._routes = []          # (regle, methodes, endpoint)
        self._views = {}
        self._map = None

    # ── Routes ────────────────────────────────────────────────────────
    def route(self, rule, methods=None):
        """Decorateur, comme Flask. La regle est relative a /api/plugins/<id>."""
        if not rule.startswith("/"):
            rule = "/" + rule

        def decorate(fn):
            endpoint = f"{fn.__name__}#{len(self._views)}"
            self._views[endpoint] = fn
            self._routes.append((rule, list(methods or ["GET"]), endpoint))
            self._map = None
            return fn
        return decorate

    def url(self, sub=""):
        return f"/api/plugins/{self.id}/{sub.lstrip('/')}"

    def _dispatch(self, sub):
        if self._map is None:
            self._map = Map([Rule(r, methods=m, endpoint=e) for r, m, e in self._routes],
                            strict_slashes=False)
        adapter = self._map.bind("localhost", path_info="/" + sub)
        try:
            endpoint, args = adapter.match(method=request.method)
        except HTTPException as e:
            return jsonify({"error": f"{self.id} : {e.name} ({request.method} /{sub})"}), e.code
        return self._views[endpoint](**args)

    # ── IA ────────────────────────────────────────────────────────────
    def config(self):
        """Configuration generale, sans la cle d'API."""
        cfg = rd_cfg()
        cfg.pop("api_key", None)
        return cfg

    def ai_unavailable(self):
        """None si l'IA est utilisable, sinon un message pour l'utilisateur."""
        cfg = rd_cfg()
        if cfg.get("key_state") == "illisible":
            return "Cle d'API illisible sur cette machine : ressaisissez-la dans Parametres."
        if not cfg.get("base_url") or not cfg.get("model"):
            return "IA non configuree : renseignez le service et le modele dans Parametres."
        if needs_key(cfg):
            return "Cle d'API manquante : configurez-la dans Parametres."
        return None

    def ai_call(self, messages, max_tokens=2000, temperature=0.5, timeout=120, temp=None):
        """Appelle le modele configure. Renvoie (texte, erreur), l'un des deux vaut None."""
        problem = self.ai_unavailable()
        if problem:
            return None, problem
        return _ai_call(rd_cfg(), messages, max_tokens=max_tokens,
                        temp=temperature if temp is None else temp, timeout=timeout)

    # ── Vault ─────────────────────────────────────────────────────────
    def vault_root(self):
        return vault_root()

    def safe_path(self, raw, must_exist=False):
        """Resout un chemin et refuse tout ce qui sort du vault (PermissionError)."""
        p = safe_path(raw)
        if must_exist and not p.exists():
            raise FileNotFoundError(str(p))
        return p

    def iter_notes(self, directory=None):
        return iter_md(str(self.safe_path(directory or vault_root())))

    def search(self, text, limit=20):
        """Recherche plein texte dans le vault : [{path, name, rel, matches:[{line, heading, text}]}].
        Les passages trouves sont encadres par les caracteres \\x01 et \\x02."""
        from .index import fresh_index
        from .index import search as query
        return query.search(fresh_index(), text, limit_files=limit)

    def note_meta(self, path):
        """En-tete de provenance d'une note : {"prisme_id": ..., "prisme_type": ...}."""
        from . import provenance as prov
        return {k: v for k, v in prov.lire(self.safe_path(path)).items() if k.startswith(prov.PREFIX)}

    def ensure_id(self, path):
        """Pose un identifiant stable sur une note et le renvoie."""
        from . import provenance as prov
        return prov.assurer_id(self.safe_path(path))

    def read_note(self, path):
        return self.safe_path(path, must_exist=True).read_text(encoding="utf-8", errors="replace")

    def write_note(self, path, content, provenance=None, *, exclusive=False):
        """Ecrit une note et declenche note_saved (ou note_created).

        provenance : dict facultatif pour une note produite par le plugin, par ex.
        {"type": "synthese", "sources": [chemin1, chemin2], "preset": "..."}.
        L'identifiant du plugin est enregistre comme outil, et un identifiant est
        pose sur chaque note citee."""
        self._require("vault_write")
        p = self.safe_path(path)
        created = not p.exists()
        if exclusive and not created:
            raise FileExistsError(str(p))
        if created and provenance is not None:
            from . import provenance as prov
            content = prov.estampiller(
                content,
                type=str(provenance.get("type") or "note"),
                outil=provenance.get("outil") or self.id,
                genere_par=str(provenance.get("genere_par") or prov.decrire_modele(rd_cfg())),
                preset=str(provenance.get("preset") or ""),
                sources=prov.sources_vers_ids(provenance.get("sources") or []),
                parent=str(provenance.get("parent") or ""))
        p.parent.mkdir(parents=True, exist_ok=True)
        snapshot(p)
        with p.open("x" if exclusive else "w", encoding="utf-8", newline="\n") as sortie:
            sortie.write(content)
        from .index import notify_changed        # import tardif : l'index importe vault/markdown
        notify_changed(p)
        hooks.emit("note_created" if created else "note_saved", path=str(p), origin=self.id)
        return p

    def typed_object(self, path):
        """Lit et valide une fiche E11 ; une édition Markdown brute n'est pas certifiée."""
        from .objets import registre, types
        obj = registre._lire(self.safe_path(path, must_exist=True))
        if obj is None:
            raise ValueError("Note sans type E11")
        titre, champs = types.valider(obj["type"], obj["titre"], obj["champs"])
        return {**obj, "titre": titre, "champs": champs}

    def set_world_clock(self, path, fields):
        """Active les bornes du monde ; le plugin doit demander le geste de l'auteur."""
        self._require("vault_write")
        from . import horloge, provenance
        p = self.safe_path(path, must_exist=True)
        meta = self.note_meta(p)
        if meta.get("prisme_type") not in ("prediction", "decision"):
            raise ValueError("L'horloge du monde concerne les décisions et prédictions")
        propres = horloge.valider(fields)
        self.safe_path(vault_root() / ".trash" / "versions")
        provenance.ecrire(p, propres)
        return self.note_meta(p)

    # ── Donnees et secrets ────────────────────────────────────────────
    def data_dir(self):
        """Dossier prive du plugin : ~/.prisme/plugins/<id>/"""
        d = DATA_DIR / "plugins" / self.id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def adopt_legacy_file(self, filename):
        """Copie ~/.secondbrain/<filename> dans data_dir() si la copie n'existe pas encore.
        Renvoie le chemin dans data_dir(). Second Brain V1 n'est jamais modifie."""
        target = self.data_dir() / filename
        source = LEGACY_DATA_DIR / filename
        if not target.exists() and source.exists() and not os.getenv("PRISME_DATA_DIR"):
            try:
                shutil.copy2(source, target)
                self.log(f"donnees reprises de {source}")
            except OSError as e:
                self.log(f"reprise impossible de {source} : {e}")
        return target

    def secret(self, name, default=""):
        """Lit un secret declare dans le manifest : coffre chiffre, puis variable d'environnement."""
        self._require("secrets")
        if name not in self._declared_secrets:
            raise PluginPermissionError(f"{self.id} : secret non declare dans le manifest : {name}")
        return secrets.plugin_secret(self.id, name) or os.getenv(name, "").strip() or default

    # ── Embeddings ────────────────────────────────────────────────────
    def register_embeddings(self, classe):
        """Declare un fournisseur d'embeddings (docs/decisions/0019).

        `classe` herite de EmbeddingProvider et recoit la configuration dans son
        __init__. C'est la porte prevue pour un modele local : le coeur ne peut pas
        embarquer une bibliotheque compilee, un plugin le peut.

            class Local(ctx.EmbeddingProvider):
                nom = "onnx"
                distant = False
            ctx.register_embeddings(Local)

        Le nom apparait alors dans Parametres > Recherche semantique.
        """
        from .vecteurs.contrat import enregistrer
        if not getattr(classe, "nom", ""):
            raise ValueError(f"{self.id} : un fournisseur d'embeddings doit porter un nom")
        enregistrer(classe)
        self.log(f"fournisseur d'embeddings : {classe.nom}")
        return classe

    EmbeddingProvider = EmbeddingProvider
    EmbeddingUnavailable = EmbeddingUnavailable

    # ── Hooks ─────────────────────────────────────────────────────────
    def on(self, event):
        """Decorateur : @ctx.on("note_saved") ; la fonction recoit path=..., origin=..."""
        def decorate(fn):
            hooks.subscribe(self.id, event, fn)
            return fn
        return decorate

    # ── Divers ────────────────────────────────────────────────────────
    def log(self, message):
        print(f"  [{self.id}] {message}")

    def _require(self, permission):
        if permission not in self.permissions:
            raise PluginPermissionError(
                f"{self.id} : permission '{permission}' non declaree dans le manifest")
