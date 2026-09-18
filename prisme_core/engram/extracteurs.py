"""Extracteurs legers, en bibliotheque standard (docs/decisions/0013).

Les formats lourds (PDF, DOCX, EPUB) viendront d'un plugin qui pilote un outil
externe : le coeur reste leger.

Exports de conversations : ChatGPT, Claude et Mistral n'ont pas le meme schema,
et ces schemas changent sans preavis. Chaque extracteur reconnait sa forme
attendue, et un extracteur generique rattrape les exports JSON de conversations
qu'aucun des trois ne reconnait, plutot que d'echouer.
"""
import html as html_mod
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser

from .contrat import Extracteur, Passage, SourceInvalide, enregistrer

ROLES = {"user": "Vous", "human": "Vous", "assistant": "Assistant", "model": "Assistant",
         "system": "Système", "tool": "Outil"}


def _date(valeur):
    """Normalise une date : horodatage Unix, ISO, ou vide."""
    if valeur in (None, "", 0):
        return ""
    try:
        if isinstance(valeur, (int, float)):
            return datetime.fromtimestamp(float(valeur), timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
        texte = str(valeur).replace("Z", "+00:00")
        return datetime.fromisoformat(texte).astimezone().strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError, OverflowError):
        return str(valeur)[:19]


def _texte_du_contenu(contenu):
    """Un message peut etre une chaine, une liste de blocs, ou un objet {parts: [...]}"""
    if contenu is None:
        return ""
    if isinstance(contenu, str):
        return contenu
    if isinstance(contenu, dict):
        for cle in ("text", "content", "value", "input", "output"):
            if isinstance(contenu.get(cle), str):
                return contenu[cle]
        if isinstance(contenu.get("parts"), list):
            return "\n".join(_texte_du_contenu(p) for p in contenu["parts"])
        return ""
    if isinstance(contenu, list):
        return "\n".join(x for x in (_texte_du_contenu(c) for c in contenu) if x)
    return str(contenu)


def _echange(role, texte, date=""):
    nom = ROLES.get(str(role).lower(), str(role).capitalize() or "Message")
    return nom, texte.strip()


def _conversation_en_passages(titre, messages, date_conv=""):
    """Un passage par message non vide, en gardant l'ordre."""
    passages = []
    for i, (role, texte, date) in enumerate(messages, 1):
        nom, propre = _echange(role, texte)
        if not propre:
            continue
        # Le titre de la conversation reste visible dans la note : sans lui, les
        # echanges de dizaines de conversations se melangeraient.
        entete = f"{titre} · {nom}" if titre else nom
        passages.append(Passage(texte=propre, titre=entete, date=date or date_conv,
                                meta={"conversation": titre, "position": i, "role": role}))
    return passages


# ── Texte et Markdown ───────────────────────────────────────────────────
@enregistrer
class ExtracteurTexte(Extracteur):
    nom = "texte"
    version = 1
    extensions = (".md", ".markdown", ".txt", ".text")

    def extraire(self, chemin, contenu):
        from ..index.segmenter import segment
        from .contrat import Extraction
        passages = [Passage(texte=s.text, titre=s.heading, meta={"lignes": [s.start_line, s.end_line]})
                    for s in segment(contenu) if s.text.strip()]
        if not passages:
            passages = [Passage(texte=contenu.strip(), titre="")]
        return Extraction(titre=chemin.stem, passages=passages, extracteur=self.nom, version=self.version)


# ── HTML ────────────────────────────────────────────────────────────────
class _Html(HTMLParser):
    IGNORE = {"script", "style", "noscript", "head"}
    BLOCS = {"p", "div", "br", "li", "tr", "section", "article", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.morceaux, self.titre, self._ignore, self._dans_titre = [], "", 0, False

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNORE:
            self._ignore += 1
        if tag == "title":
            self._dans_titre = True
        if tag in self.BLOCS:
            self.morceaux.append("\n")

    def handle_endtag(self, tag):
        if tag in self.IGNORE and self._ignore:
            self._ignore -= 1
        if tag == "title":
            self._dans_titre = False
        if tag in self.BLOCS:
            self.morceaux.append("\n")

    def handle_data(self, data):
        if self._dans_titre:
            self.titre += data.strip()
        elif not self._ignore and data.strip():
            self.morceaux.append(data.strip())


@enregistrer
class ExtracteurHtml(Extracteur):
    nom = "html"
    version = 1
    extensions = (".html", ".htm", ".xhtml")

    def extraire(self, chemin, contenu):
        from .contrat import Extraction
        parseur = _Html()
        parseur.feed(contenu)
        texte = re.sub(r"\n{3,}", "\n\n", " ".join(parseur.morceaux).replace(" \n ", "\n"))
        blocs = [b.strip() for b in texte.split("\n\n") if b.strip()]
        passages, tampon = [], []
        for bloc in blocs:                        # regroupement vers ~1 500 caracteres
            tampon.append(bloc)
            if sum(len(x) for x in tampon) > 1500:
                passages.append(Passage(texte="\n\n".join(tampon)))
                tampon = []
        if tampon:
            passages.append(Passage(texte="\n\n".join(tampon)))
        return Extraction(titre=html_mod.unescape(parseur.titre) or chemin.stem, passages=passages,
                          extracteur=self.nom, version=self.version)


# ── Exports de conversations ────────────────────────────────────────────
class _ExtracteurConversations(Extracteur):
    extensions = (".json",)

    def reconnait(self, chemin, debut):
        return chemin.suffix.lower() == ".json"

    def conversations(self, data):
        raise NotImplementedError

    def extraire(self, chemin, contenu):
        from .contrat import Extraction
        data = self.json_charge(contenu, chemin)
        convs = list(self.conversations(data))
        if not convs:
            raise SourceInvalide(f"{chemin.name} : aucune conversation reconnue par l'extracteur {self.nom}")
        passages = []
        for titre, date, messages in convs:
            passages.extend(_conversation_en_passages(titre, messages, date))
        # Un export d'une seule conversation prend son titre ; au-dela, le nom du fichier
        titre_note = convs[0][0] if len(convs) == 1 and convs[0][0] else chemin.stem
        return Extraction(titre=titre_note, passages=passages, extracteur=self.nom,
                          version=self.version, meta={"conversations": len(convs)})


@enregistrer
class ExtracteurChatGpt(_ExtracteurConversations):
    """Export ChatGPT : conversations.json, arbre de messages relie par parent/children."""
    nom = "chatgpt"
    version = 1

    def reconnait(self, chemin, debut):
        return chemin.suffix.lower() == ".json" and b'"mapping"' in debut[:4096]

    def conversations(self, data):
        for conv in data if isinstance(data, list) else [data]:
            if not isinstance(conv, dict) or "mapping" not in conv:
                continue
            mapping = conv["mapping"] or {}
            # On suit la chaine depuis la racine : l'ordre des echanges est celui de l'arbre
            enfants, racine = {}, None
            for cle, noeud in mapping.items():
                parent = (noeud or {}).get("parent")
                enfants.setdefault(parent, []).append(cle)
                if parent is None:
                    racine = cle
            messages, pile = [], [racine]
            while pile:
                cle = pile.pop(0)
                noeud = mapping.get(cle) or {}
                msg = noeud.get("message") or {}
                auteur = ((msg.get("author") or {}).get("role")) or ""
                texte = _texte_du_contenu(msg.get("content"))
                if texte.strip() and auteur != "system":
                    messages.append((auteur, texte, _date(msg.get("create_time"))))
                pile = (noeud.get("children") or enfants.get(cle, []))[:1] + pile
            if messages:
                yield conv.get("title") or "Conversation", _date(conv.get("create_time")), messages


@enregistrer
class ExtracteurClaude(_ExtracteurConversations):
    """Export Claude : liste de conversations avec chat_messages."""
    nom = "claude"
    version = 1

    def reconnait(self, chemin, debut):
        return chemin.suffix.lower() == ".json" and b'"chat_messages"' in debut[:4096]

    def conversations(self, data):
        for conv in data if isinstance(data, list) else [data]:
            if not isinstance(conv, dict) or "chat_messages" not in conv:
                continue
            messages = []
            for msg in conv.get("chat_messages") or []:
                texte = _texte_du_contenu(msg.get("content")) or msg.get("text") or ""
                if texte.strip():
                    messages.append((msg.get("sender") or msg.get("role") or "", texte,
                                     _date(msg.get("created_at"))))
            if messages:
                yield conv.get("name") or conv.get("title") or "Conversation", \
                    _date(conv.get("created_at")), messages


@enregistrer
class ExtracteurMistral(_ExtracteurConversations):
    """Export Le Chat (Mistral).

    Le format n'est pas documente publiquement et a deja change : on reconnait
    ici les formes observees (une liste de conversations avec `messages`, ou un
    objet contenant `conversations`/`chats`), et l'extracteur generique prend le
    relais pour toute autre forme."""
    nom = "mistral"
    version = 1

    MARQUEURS = (b"mistral", b"le chat", b"lechat")

    def reconnait(self, chemin, debut):
        if chemin.suffix.lower() != ".json":
            return False
        tete = debut[:4096].lower()
        if b'"mapping"' in tete or b'"chat_messages"' in tete:
            return False
        return any(m in tete for m in self.MARQUEURS) or "mistral" in chemin.name.lower()

    def conversations(self, data):
        blocs = data
        if isinstance(data, dict):
            for cle in ("conversations", "chats", "data", "items"):
                if isinstance(data.get(cle), list):
                    blocs = data[cle]
                    break
            else:
                blocs = [data]
        for conv in blocs if isinstance(blocs, list) else []:
            if not isinstance(conv, dict):
                continue
            liste = None
            for cle in ("messages", "chat_messages", "entries", "history"):
                if isinstance(conv.get(cle), list):
                    liste = conv[cle]
                    break
            if liste is None:
                continue
            messages = []
            for msg in liste:
                if not isinstance(msg, dict):
                    continue
                texte = _texte_du_contenu(msg.get("content") or msg.get("text") or msg.get("message"))
                role = msg.get("role") or msg.get("author") or msg.get("sender") or ""
                if texte.strip():
                    messages.append((role, texte, _date(msg.get("created_at") or msg.get("createdAt")
                                                        or msg.get("timestamp"))))
            if messages:
                yield (conv.get("title") or conv.get("name") or conv.get("subject") or "Conversation",
                       _date(conv.get("created_at") or conv.get("createdAt")), messages)


@enregistrer
class ExtracteurConversationsGenerique(_ExtracteurConversations):
    """Dernier recours : tout JSON qui ressemble a des conversations (role + contenu)."""
    nom = "conversations"
    version = 1
    config = "detection automatique"

    def reconnait(self, chemin, debut):
        return chemin.suffix.lower() == ".json"

    def conversations(self, data):
        yield from ExtracteurMistral().conversations(data)
        if isinstance(data, list) and data and isinstance(data[0], dict) and "role" in data[0]:
            messages = [(m.get("role", ""), _texte_du_contenu(m.get("content")),
                         _date(m.get("created_at"))) for m in data if isinstance(m, dict)]
            messages = [m for m in messages if m[1].strip()]
            if messages:
                yield "Conversation", "", messages


@enregistrer
class ExtracteurJsonBrut(Extracteur):
    """JSON qui n'est pas une conversation : on garde le document lisible."""
    nom = "json"
    version = 1
    extensions = (".json",)

    def extraire(self, chemin, contenu):
        from .contrat import Extraction
        data = self.json_charge(contenu, chemin)
        texte = json.dumps(data, ensure_ascii=False, indent=2)
        morceaux = [texte[i:i + 3000] for i in range(0, len(texte), 3000)]
        return Extraction(titre=chemin.stem, extracteur=self.nom, version=self.version,
                          passages=[Passage(texte="```json\n" + m + "\n```", titre=f"Bloc {i}")
                                    for i, m in enumerate(morceaux, 1)])
