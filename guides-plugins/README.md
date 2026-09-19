# Guides des plugins de PRISME

Ces guides accompagnent les **neuf plugins présents dans le dépôt**. Ils décrivent
l'interface intégrée à PRISME, après les PR #19 et #20. Commencez par un petit vault
d'essai : un vault est simplement le dossier contenant vos notes Markdown.

## Choisir le bon guide

| Bouton dans PRISME | Guide | Usage principal |
|---|---|---|
| ArXiv | [Recherche scientifique](arxiv.md) | Trouver des publications et synthétiser leurs résumés |
| DDG | [Recherche web](duckduckgo.md) | Rechercher sur le Web depuis une note |
| Multi-sélection | [Context Builder](context.md) | Poser une question sur plusieurs notes choisies |
| Prompts | [Prompts Manager](prompts.md) | Réutiliser des consignes de réponse |
| RSS | [Veille RSS](rss.md) | Suivre des flux et comparer leurs articles |
| OSINT | [OSINT Cross-Reference](osint-cx.md) | Examiner et recouper des indices publics |
| Embeddings | [Embeddings locaux](embeddings-locaux.md) | Configurer une recherche par le sens sur la machine |
| Constat | [Dossiers et analyse ACH](constat.md) | Constituer un corpus et confronter des hypothèses |
| Calibration | [Évaluer ses prédictions](calibration.md) | Comparer les probabilités annoncées aux résultats observés |

Pour le parcours complet **Constat → prédiction → Calibration**, suivez d'abord
[le dossier de démonstration](constat.md), puis [le premier score](calibration.md).
Le classement ACH, le score OSINT et les scores de calibration mesurent des choses
différentes : aucun ne se convertit automatiquement en probabilité.

## Avant le premier usage

1. Ouvrez PRISME et choisissez votre vault dans les paramètres.
2. Ouvrez **Plugins** et vérifiez que le plugin voulu est présent et actif.
3. Pour un module utilisant l'IA, configurez dans les paramètres PRISME l'URL du
   service, le modèle et, si ce service en exige une, sa clé. Testez la connexion.
4. Après installation d'un plugin ou changement de dépendances, arrêtez et relancez
   PRISME. Rechargez la page avec **Ctrl+F5** si l'ancien affichage persiste.

Le code des plugins se trouve dans `plugins/`, à côté du lanceur. Les versions
sources se lancent depuis la racine du dépôt :

```powershell
python prisme.py
```

La distribution Windows est en cours de validation à l'étape E9. Dans son archive,
`PRISME.exe`, `_internal/`, `plugins/` et ce dossier de guides restent côte à côte.
Double-cliquer sur l'exécutable lance l'application sans installation de Python.
Sans `plugins/`, seules les fonctions du cœur sont disponibles. Consulter le
[parcours de vérification E9](../docs/branches/e9-publication.md) avant publication.

## Comprendre les données utilisées

| Plugin | IA configurée dans PRISME | Autres communications |
|---|---|---|
| ArXiv | Requête et synthèse | Recherche sur arXiv |
| DDG | Requête et synthèse | Moteurs de recherche et pages consultées |
| Context Builder | Réponse sur le corpus sélectionné | Aucune recherche web propre au plugin |
| Prompts Manager | Aucune pour gérer les presets | Aucune pour gérer les presets |
| RSS | Synthèse ; les comptages lexicaux sont locaux | Flux et articles sélectionnés |
| OSINT | Aucune | Sources cochées et outils externes éventuels |
| Embeddings locaux | Aucun modèle conversationnel requis | Téléchargement du modèle ; inférence locale ensuite |
| Constat | Étapes d'analyse lancées explicitement | Appel au fournisseur IA configuré |
| Calibration | Aucune | Aucune |

**PRISME local ne signifie pas que le fournisseur IA est local.** Avec un service
IA distant, le contenu envoyé pour l'analyse quitte la machine. Le plugin
Embeddings locaux ne rend pas les autres appels IA locaux.

Le profil PRISME est normalement `%USERPROFILE%\.prisme` sous Windows ;
`PRISME_DATA_DIR` peut le déplacer. Les guides distinguent ce profil du vault.
Pour une sauvegarde complète, conservez vos notes **et** les données utiles du
profil, notamment les presets et les dossiers Constat. Les rapports restent dans
le vault ; les réglages ne sont pas tous stockés avec eux.

Les secrets des plugins se saisissent dans **Plugins → plugin concerné → Secrets**.
Ils sont chiffrés sous Windows. Un fichier `.env`, lorsqu'il est utilisé, reste du
texte en clair : ne l'ajoutez pas à une PR ou à une archive de distribution.

## Si un bouton manque

- Plugin absent du gestionnaire : vérifiez la présence de son dossier et de son
  `manifest.json`. Un dossier vide ou contenant seulement des caches Python n'est
  pas une installation.
- Plugin désactivé : réactivez-le, puis rechargez l'interface.
- Plugin en erreur ou incompatible : lisez le message du gestionnaire et du terminal.
  Une clé manquante et une dépendance Python manquante sont deux problèmes distincts.
- Depuis Git, vérifiez la branche avec `git branch --show-current`. Un plugin
  présent uniquement sur une autre branche n'apparaît pas dans celle lancée.

Les guides décrivent les connecteurs inclus dans le code ; ils ne garantissent
ni la disponibilité des services tiers, ni la qualité des réponses d'un modèle.
En cas de divergence avec une ancienne notice dans `plugins/`, utilisez ce dossier
pour le parcours utilisateur actuel.
