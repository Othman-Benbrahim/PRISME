# Embeddings locaux — rechercher par le sens avec ONNX

[Retour aux guides](README.md)

## À quoi sert ce plugin ?

Un *embedding* est une représentation numérique d'un texte permettant de comparer
son sens à celui d'autres textes. Ce plugin exécute un modèle sur le processeur de
votre machine. Il fournit **onnx** à la recherche sémantique du cœur PRISME.

Il ne rédige pas de réponse et ne remplace pas le modèle conversationnel. Il y a
**deux réglages distincts** : préparer le modèle dans **Embeddings**, puis activer
son utilisation dans **Paramètres → Recherche sémantique**.

## Installer les dépendances dans la version source

**Version source :** dans le même environnement Python que celui qui lance PRISME :

```powershell
Set-Location "D:\Documents\PRISME\PRISME-depot"
python -m pip install -r plugins/embeddings-locaux/requirements.txt
```

Arrêtez et relancez PRISME. Le panneau doit confirmer que **onnxruntime** et
**tokenizers** sont installés. Si elles manquent, le plugin peut rester visible,
mais son fournisseur est indisponible : visible ne signifie pas prêt à vectoriser.
**Distribution Windows E9 :** ONNX Runtime et tokenizers sont livrés dans `_internal/`.
Aucune commande pip n'est nécessaire. Si le panneau signale leur absence, réextraire
l'archive entière avec `_internal/`, puis relancer. Le modèle reste à préparer ci-dessous.

## Préparer un modèle

1. Ouvrez **Embeddings**.
2. Choisissez l'une des deux voies :
   - un dossier local contenant **`model.onnx`** et **`tokenizer.json`**, puis
     **Utiliser ce dossier** ;
   - un modèle du catalogue et **Télécharger**, puis confirmer le téléchargement.
3. Attendez l'indication de fin et vérifiez **Modèle en place**.
4. Gardez **Préfixes e5 (« query: » / « passage: »)** cochés pour les modèles e5.
5. Cliquez sur **Essayer le modèle**. Le résultat affiche les dimensions, le temps
   et la similarité de phrases proches comparée à celle de phrases sans rapport.
6. Facultativement, cliquez sur **Épingler l'empreinte** après avoir choisi une
   source de confiance : un prochain téléchargement différent sera refusé.

Le catalogue contient des variantes multilingues e5 small et base. Un modèle plus
volumineux n'est pas automatiquement meilleur pour vos notes. L'essai intégré
est un contrôle de fonctionnement sur quelques phrases, pas une évaluation de
votre corpus. Les préfixes inadaptés peuvent dégrader les résultats sans erreur technique.

Le réglage **fils** limite les threads CPU ; **0** laisse le choix automatique.
Si la machine devient peu réactive, réduisez cette valeur puis appliquez les réglages.

## Activer et vectoriser

1. Ouvrez **Paramètres → Recherche sémantique**.
2. Cochez **Recherche sémantique** et choisissez le fournisseur **onnx**.
3. Enregistrez les réglages et utilisez **Tester**.
4. Cliquez sur **Vectoriser le vault** et attendez la fin de l'opération.
5. Essayez une recherche avec une reformulation d'un sujet présent dans vos notes.
   Comparez les résultats avec une recherche par mots connus.

Une collection vide de vecteurs ne peut pas restituer une recherche sémantique
utile. Après changement de modèle, reconstruisez les vecteurs ; ne mélangez pas
les représentations de modèles différents. **Effacer les vecteurs** retire
l'index vectoriel, pas les notes Markdown. Vérifiez l'état de vectorisation quand
vous ajoutez ou modifiez beaucoup de notes.

## Données, stockage et limites

Une fois le modèle téléchargé, l'inférence ONNX est locale : les notes et requêtes
traitées par ce fournisseur ne sont pas envoyées à une API d'embeddings. Le
téléchargement contacte néanmoins son hébergeur. Les autres fonctions IA de
PRISME suivent leurs propres paramètres et peuvent utiliser un service distant.

Les modèles téléchargés et réglages vivent normalement sous
`%USERPROFILE%\.prisme\plugins\embeddings-locaux\`. Un dossier de modèle choisi
manuellement peut se trouver ailleurs. Les index vectoriels sont reconstruisibles
à partir des notes ; une sauvegarde de vos notes n'inclut pas automatiquement le modèle.

Le moteur limite chaque texte à **512 jetons**. Une ressemblance calculée n'est ni
une preuve de vérité ni une garantie que tous les passages importants ont été vus.
L'empreinte épinglée détecte un changement de fichier ; elle ne certifie pas à elle
seule l'identité de son auteur ou la qualité du modèle.

## Dépannage

| Symptôme | Que faire ? |
|---|---|
| Dépendances absentes | Vérifier le Python utilisé pour pip et pour PRISME ; relancer l'application |
| Modèle incomplet | Vérifier les deux fichiers attendus et le dossier choisi |
| ONNX illisible | Vérifier qu'il s'agit d'un modèle compatible et que le téléchargement est complet |
| Téléchargement refusé pour empreinte | Examiner le changement de source ou de fichier avant toute décision |
| Fournisseur absent | Activer le plugin et redémarrer PRISME |
| Recherche seulement lexicale | Vérifier activation sémantique, fournisseur, modèle et vectorisation |
| Mauvais résultats sans erreur | Vérifier les préfixes e5 et tester sur vos propres questions de référence |

**Repère de réussite :** modèle essayé, fournisseur onnx disponible, vecteurs créés,
et résultats pertinents sur plusieurs reformulations que vous pouvez contrôler.
