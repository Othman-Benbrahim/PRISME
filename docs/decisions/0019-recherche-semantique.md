# 0019 · Recherche sémantique

- **Statut** : acceptée, non encore appliquée
- **Écrite** : 2026-09-16

**Retenu.** Interface « fournisseur d'embeddings » dans le cœur, avec trois voies :
plugin local ONNX Runtime + modèle e5 (exception assumée à la règle de dépendances :
bibliothèque compilée dans le plugin, modèle téléchargé à part) ; API compatible OpenAI
(`/embeddings`) avec paramétrage séparé du chat ; Ollama.

**Règles.** Pas de mélange de modèles dans un index (changement = revectorisation annoncée) ;
mode distant désactivé par défaut, avec avertissement ; mode actif toujours visible ;
fusion FTS5 + vecteurs par RRF (k = 60) puis diversification ; repli sur FTS5 seul en cas
d'absence ou de panne ; vecteurs réutilisés par empreinte de segment.
