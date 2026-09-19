# Prompts Manager — réutiliser ses consignes

[Retour aux guides](README.md)

## À quoi sert ce plugin ?

Un **preset** est un texte de consignes réutilisable : langue, structure, exigences
de citation, distinction entre faits et hypothèses. Il oriente une réponse ; il
n'ajoute ni sources, ni connaissances garanties, ni capacités au modèle.

Créer et modifier les presets ne nécessite aucune IA et ne lance aucun appel réseau.

## Créer un premier preset

1. Ouvrez **Prompts**, puis **+ Nouveau preset**.
2. Donnez un nom, par exemple « Synthèse sourcée ».
3. Dans **Contenu du prompt système**, saisissez :

```text
Réponds en français. Distingue les faits documentés, les hypothèses et les incertitudes.
Cite les sources fournies pour chaque conclusion importante.
Si le corpus ne répond pas à la question, indique ce qui manque sans l'inventer.
```

4. Cliquez sur **Sauver**. Le preset apparaît dans la liste.
5. Fermez et rouvrez le gestionnaire pour vérifier sa conservation.

Pour modifier un preset, sélectionnez-le à gauche, changez son texte et cliquez
sur **Sauver**. **Annuler** abandonne les changements non enregistrés.

## Appliquer le preset

Dans l'interface actuelle, **DDG** et **RSS** proposent **Choisir un preset…** à côté
du champ **Prompt système**. Sélectionnez votre preset, relisez le texte inséré,
puis lancez l'analyse depuis le plugin concerné.

Le choix copie le contenu dans le champ : il ne déclenche pas l'analyse et ne
crée pas une liaison permanente. Si vous modifiez ensuite le preset dans le
gestionnaire, sélectionnez-le à nouveau dans le formulaire pour actualiser le texte.

Pour **Multi-sélection**, copiez et collez le texte dans son champ Prompt système.
ArXiv n'expose pas ce champ ; Constat utilise ses consignes méthodologiques par
étape. Le gestionnaire ne remplace pas automatiquement tous les prompts de PRISME.

## Supprimer ou restaurer

- **Supprimer** retire le preset choisi après confirmation.
- **Restaurer les défauts** remplace la liste par les presets d'origine : vos
  personnalisations sont écrasées. Sauvegardez-les d'abord si vous voulez les garder.
- Un preset de prévision qui demande des probabilités à un modèle ne les transforme
  pas en prédictions validées : le [parcours Calibration](calibration.md) reste distinct.

## Stockage et dépannage

Les presets sont enregistrés dans
`%USERPROFILE%\.prisme\plugins\prompts\system_prompts.json`, sauf profil déplacé
avec `PRISME_DATA_DIR`. Ils appartiennent au profil et sont partagés entre ses vaults.
Ce fichier est du texte JSON, non un coffre de secrets : n'y placez pas de clé API.
L'ancien chemin `~/.secondbrain/system_prompts.json` encore affiché dans le pied de
fenêtre est un libellé historique ; ce n'est pas le chemin de stockage PRISME actuel.

| Symptôme | Que faire ? |
|---|---|
| « Nom requis » ou « Contenu requis » | Remplir les deux champs avant de sauver |
| Le preset n'apparaît pas dans un formulaire | Vérifier que le plugin propose le sélecteur ; recharger PRISME après activation de Prompts |
| Anciennes consignes encore visibles | Choisir à nouveau le preset dans le formulaire |
| Liste revenue aux défauts | Vérifier le profil utilisé et l'état du fichier JSON ; un fichier illisible entraîne un repli sur les défauts |

**Repère de réussite :** le preset survit à la réouverture et son texte est visible
dans le champ du plugin avant le lancement de l'analyse.
