# 0011 · Double granularité

- **Statut** : acceptée, non encore appliquée
- **Écrite** : 2026-09-16

**Retenu.** Une table par fichier (tags, liens, graphe) et une table par segment (recherche).

**Découpage.** Un segment par titre de niveau 1 à 3 ; notes sans titres : paragraphes
regroupés vers 1 500 caractères ; sections longues redécoupées au-delà d'environ 4 000
caractères, sur une fin de paragraphe. Blocs de code jamais coupés. Chaque segment porte
sa note, son titre, sa position et une empreinte de contenu.
