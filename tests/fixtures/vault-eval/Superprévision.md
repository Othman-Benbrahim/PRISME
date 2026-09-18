# Superprévision

La superprévision repose sur la calibration : un prévisionniste annonce une
probabilité et accepte d'être scoré. Le score de Brier mesure l'écart entre la
probabilité annoncée et le résultat observé.

## Mise à jour bayésienne

Une observation nouvelle révise le prior en posterior. Le rapport de
vraisemblance porte toute la force de la révision.

## Indicateurs de bascule

Un indicateur de bascule est un fait observable qui, s'il survient, oblige à
réviser la prévision. Voir [[Signaux faibles]].
