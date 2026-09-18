# E4 — ENGRAM : ingestion des sources

## Objectif

Faire entrer des sources extérieures dans le vault sans créer de doublon, en
gardant la trace de ce qui vient d'où, et en conservant les identifiants des
passages d'un import à l'autre. Décisions appliquées :
[0013](../decisions/0013-engram-toutes-les-sources-un-seul-contrat.md),
[0014](../decisions/0014-forme-des-notes-importees.md),
[0015](../decisions/0015-fichiers-d-origine.md),
[0016](../decisions/0016-passages-retires-d-une-source.md).

## Ce qui change

**Un contrat d'extraction commun.** Avant de lire un fichier, PRISME le vérifie
(existence, taille, format), calcule son empreinte **avant et après** la lecture, et
refuse l'import si le fichier a changé entre les deux. Il enregistre quel extracteur
l'a lu, dans quelle version. Si un extracteur ne trouve rien, le suivant prend le
relais : un JSON qui n'est pas une conversation finit lisible plutôt qu'en erreur.

**Six extracteurs légers**, en bibliothèque standard :

| Extracteur | Formats |
|---|---|
| `chatgpt` | export ChatGPT (`conversations.json`, arbre `mapping`) |
| `claude` | export Claude (`chat_messages`) |
| `mistral` | export Le Chat |
| `conversations` | tout JSON de conversations qu'aucun des trois ne reconnaît |
| `texte` | `.md`, `.markdown`, `.txt` (découpés par le segmenteur d'E2) |
| `html` | `.html`, `.htm` (scripts et styles écartés) |
| `json` | dernier recours : le document reste lisible |

**Sur Mistral, une réserve.** Le format de l'export Le Chat n'est pas documenté
publiquement et a déjà changé. L'extracteur reconnaît les formes observées (liste de
conversations avec `messages`, objet contenant `conversations` ou `chats`) et
l'extracteur générique rattrape le reste. **À valider avec un vrai export** : si le
tien n'est pas reconnu, envoie-moi les premières lignes du fichier et j'ajuste.

**L'identité des passages survit aux modifications.** Algorithme repris de Studio
Littéraire : même position et même texte, puis texte identique déplacé et unique, puis
texte retouché à au moins 65 % de ressemblance avec 8 points d'avance sur le meilleur
rival. Dans le doute, nouvel identifiant plutôt que rattachement hasardeux.

**Les identifiants vivent dans le vault**, pas dans une base à part : chaque passage
porte une ancre de bloc Obsidian (`^p-xxxxxxxx`). Un réimport relit les notes
existantes pour retrouver les identifiants. Supprimer le registre du profil ne perd
donc rien d'essentiel.

**Idempotence.** Réimporter une source inchangée ne réécrit rien et le dit. Une source
modifiée ne fait réécrire que ce qui a bougé, et le rapport donne les comptes :
nouveaux, inchangés, déplacés, modifiés, retirés.

**Les passages disparus sont archivés, pas supprimés** : encadré `> [!danger]` en fin
de note, avec la date et l'empreinte de la version de la source responsable, affiché
en rouge par Obsidian comme par PRISME. Un passage qui réapparaît quitte l'archive.

**Une note par source**, répartie en parties au-delà du seuil (200 000 caractères par
défaut), reliées par une note sommaire. La coupure tombe toujours entre deux passages.

**Copie ou référence, au choix.** En mode référence, le fichier reste où il est ; en
mode copie, il est copié dans `_sources/` du vault. La provenance garde dans les deux
cas l'empreinte, le chemin d'origine et le mode.

**Contrôle des sources** : la liste des sources suivies indique si chacune est intacte,
modifiée ou disparue, et permet de réimporter ou d'oublier.

**Interface** : bouton 📥 Sources. On donne le **chemin** du fichier ; rien ne transite
par le navigateur, donc aucune limite de taille pour un export de plusieurs centaines
de mégaoctets.

## Fichiers touchés

**Créés** : `prisme_core/engram/` (`contrat.py`, `extracteurs.py`, `identite.py`,
`notes.py`, `ingestion.py`), `prisme_core/routes/engram.py`, `web/js/engram.js`,
`web/css/engram.css`, `tests/test_e4_engram.py`, `tests/fixtures/exports/` (4 exports
de test), ce fichier.

**Modifiés** : `prisme_core/app.py`, `web/index.html`, `docs/ARCHITECTURE.md`,
`docs/RUPTURES.md`, `docs/FEUILLE-DE-ROUTE.md`, `docs/decisions/0013` à `0016`,
`docs/decisions/README.md`.

## Tester

```powershell
python -m unittest discover -s tests -v
python prisme.py
```

114 tests, dont 21 pour E4 : extracteurs (dont un test qui modifie le fichier pendant
la lecture pour vérifier le refus), identité des passages, import, réimport identique,
source modifiée, passage retiré puis revenu, mode copie, découpage en parties,
contrôle des sources, routes.

Vérifications manuelles :

1. 📥 Sources, coller le chemin d'un **vrai export** (ChatGPT, Claude ou Mistral),
   Vérifier : l'extracteur reconnu doit s'afficher. Importer, puis ouvrir la note.
2. Réimporter le même fichier : PRISME doit répondre « déjà importée, à l'identique ».
3. Modifier la source (ou en réexporter une version plus récente) et réimporter : les
   comptes doivent montrer ce qui a changé, et les passages inchangés garder leur ancre.
4. Chercher un mot de la source : la note importée doit sortir dans les résultats.
5. Ouvrir la note dans Obsidian : les ancres `^p-…` et l'encadré rouge doivent
   s'afficher normalement.

Vérifié ici dans un navigateur réel : import Mistral puis ChatGPT, réimport identique
refusé, mode copie, registre des sources, ouverture de la note, recherche sur le
contenu importé, aucune erreur JavaScript.

## Limites connues

- **Extracteurs lourds absents** : PDF, DOCX, EPUB et OCR viendront d'un plugin
  séparé qui pilote un outil externe, pour que le cœur reste léger.
- **Le signal des passages retirés ne se propage pas encore** aux notes qui les
  citent : l'archive est marquée dans la note de la source, mais PRISME ne va pas
  modifier vos notes pour y ajouter un avertissement. La détection des citations
  orphelines viendra avec les objets (E5).
- Un import se fait par **chemin de fichier** : pas de glisser-déposer.
- Le format Mistral est inféré, pas documenté (voir plus haut).
- Une source renommée sur le disque est vue comme disparue ; il faut la réimporter
  depuis son nouveau chemin, et les identifiants de passages sont alors conservés
  seulement si l'ancienne note est encore présente.

## Hors périmètre

File de validation et objet Source (E5), API à clés pour les agents (E6).
