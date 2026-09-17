# 0022 · Horloges des objets

- **Statut** : acceptée, non encore appliquée (E3)
- **Écrite** : 2026-09-17

Inspirée d'Utopia (fiches 0019 et 0022).

## Problème

Pour évaluer honnêtement une prédiction, il faut savoir ce que PRISME tenait pour vrai **au moment** où elle a été faite. Il faut aussi distinguer « quand c'était vrai dans le monde » de « quand PRISME l'a enregistré ».

## Décision

- **Horloge d'enregistrement, active dès E3** : `prisme_enregistre_le` (entrée dans PRISME, directe ou validée) et `prisme_invalide_le` (retrait ; vide tant que l'objet est tenu pour valable).
- **Horloge du monde, réservée mais inactive** : `prisme_valide_du` et `prisme_valide_au`. Elle servira aux décisions et prédictions.
- Les sources portent leur date de publication dans `prisme_publie_le` (métadonnée, pas une horloge).
- **Une date inconnue n'est pas une date ouverte.** Chaque champ date a un compagnon d'état : `<champ>_etat: date | inconnue | ouverte`. Le champ date reste une vraie date pour Obsidian, qui n'admet qu'un type par propriété.
- Les passages n'ont pas ces champs : leur apparition et leur retrait vivent dans l'index (et dans le callout de [0016](0016-passages-retires-d-une-source.md)).
- Un objet retiré garde une ligne minimale dans l'index (identifiant, dates, raison), pour pouvoir répondre à « que tenait-on pour vrai à telle date ».

## Point ouvert

Les prédictions demanderont un archivage plus solide que la corbeille.

## Écarté

- Les deux horloges partout, y compris sur les passages (horloge du monde vide pour du texte).
- Les deux horloges actives sur les objets dès maintenant (inutile tant que seul le type Source existe).
