# Évaluation de la recherche

`questions-reference.jsonl` contient des questions dont on connaît la réponse
attendue, posées sur le vault de référence `tests/fixtures/vault-eval/`.
Le test `TestQuestionsDeReference` (dans `tests/test_e2_index.py`) vérifie que la
note attendue figure dans les trois premiers résultats.

Une ligne = une question :

```json
{"id": "q3", "question": "bayesienne", "attendu": "Superprévision.md", "raison": "insensible aux accents"}
```

Le principe vient du RAG de Studio Littéraire et de la roadmap Lux Kybernetica :
une recherche ne se juge pas « à l'œil », elle se mesure sur des cas connus.

**Ajouter une question** quand une recherche vous a déçu : écrivez le cas ici,
ajoutez au besoin une note au vault de référence, puis corrigez le moteur.
La liste ne doit contenir que des cas qui comptent, pas des cas faciles.

Couverture actuelle : mot exact, préfixe partiel, absence d'accents, plusieurs
mots dans des segments différents, titre de section, sous-dossier, nom de
fichier, vocabulaire isolé.
