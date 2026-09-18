# 0024 · Synchronisation entre machines

- **Statut** : acceptée, non encore appliquée
- **Écrite** : 2026-09-19

## Problème

Un vault en `.md` se synchronise sans peine (Syncthing, un dossier cloud, un dépôt git).
Le reste de l'état de PRISME vit dans le profil `~/.prisme/`, qui ne suit pas. Certaines
de ces données sont des **jugements de l'auteur** : rejeter une source en écrivant « pas
une source, une opinion » est une décision, pas un cache. Aujourd'hui elle reste sur la
machine où elle a été prise, et l'autre machine repropose la même chose sans savoir
pourquoi elle avait été refusée.

## Décision

Classer chaque état selon sa nature, et faire suivre le vault à ce qui est de l'auteur.

| Nature | Exemples | Règle |
|---|---|---|
| **Dérivable** | index SQLite, registre ENGRAM | **Jamais synchronisé.** Se reconstruit seul. Une base SQLite dans un dossier synchronisé finit corrompue. |
| **Propre à la machine** | `config.json` (chemin du vault, clé chiffrée DPAPI), clés d'agent, journal | **Jamais synchronisé.** Un blob DPAPI est illisible ailleurs par construction (0023) ; une clé d'agent ouvre une API locale. |
| **De l'auteur** | objets Source, **rejets et leurs raisons** | **Suit le vault.** |

- Les objets Source sont déjà dans le vault (0017, appliqué en E5) : rien à changer.
- **Les rejets mémorisés descendent dans le vault**, à côté des objets.
- **Format append-only** (JSONL, une ligne par rejet, dédoublonné à la lecture) : un JSON
  réécrit en entier produit un conflit à chaque synchronisation ; des lignes ajoutées se
  recollent, et une copie de conflit s'absorbe en concaténant.
- **La file d'attente reste locale.** Une proposition non traitée est un travail en
  cours, pas une décision : la synchroniser apporterait des conflits sans bénéfice.
- Un **fichier de présence** dans le vault permet d'avertir quand deux instances
  regardent le même vault synchronisé. Avertir, pas verrouiller.

## Assumé

Le dernier qui écrit gagne, comme aujourd'hui. La synchronisation augmente la fréquence
des écritures concurrentes mais ne change pas la règle ; `.trash/versions/` reste le
filet. Un verrouillage réparti serait hors de proportion pour un outil local.

## Écarté

- Synchroniser le profil entier : corrompt l'index et transporte des secrets non
  portables.
- Une base de données partagée ou un serveur : contraire à la nature locale de l'outil
  (0010).

## Reste à trancher

Les données de plugins (bibliothèque de prompts, par exemple) sont dans le profil alors
que certaines sont clairement de l'auteur. L'API des plugins devra permettre de déclarer
« mes données vivent dans le vault ». Non urgent.
