# 0020 · Méthode de travail

- **Statut** : appliquée depuis l'étape 00
- **Écrite** : 2026-09-16

**Retenu.** Fichiers préparés localement, poussés avec PowerShell et GitHub CLI. Une branche
documentée par étape, une pull request par étape validée. Tests en `unittest` (bibliothèque
standard) avant chaque pull request, et questions de référence pour la recherche.

## Révision du 2026-09-21 — le texte ne transite pas par PowerShell

Les corps des pull requests 24, 25 et 26 ont été publiés en charabia : `â€”` pour un
tiret cadratin, `Ã©` pour un `é`. Le script de livraison recopiait `PR.md` avant de le
passer à `gh` :

```powershell
Set-Content -Path $tmp -Value (Get-Content -Raw -Path "PR.md") -Encoding UTF8   # NON
```

`Get-Content` sans `-Encoding` lit en ANSI sous Windows PowerShell 5.1. Le fichier est en
UTF-8 : ses octets sont donc décodés comme du cp1252, puis réencodés en UTF-8. Chaque
caractère accentué passe deux fois à la machine et en ressort doublé. `-Encoding UTF8`
ajoute par-dessus une marque d'ordre des octets que `gh` transmet telle quelle.

**Règle.** Un fichier de texte destiné à un outil qui lit de l'UTF-8 lui est passé
**directement**, jamais recopié :

```powershell
gh pr create --body-file (Join-Path $Source "PR.md")
```

Si une recopie est inévitable, elle passe par .NET, qui ne devine rien :

```powershell
$texte = [System.IO.File]::ReadAllText($source, [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText($cible, $texte, (New-Object System.Text.UTF8Encoding($false)))
```

Les messages de commit n'étaient pas touchés : ils vivent dans le `.ps1` lui-même, écrit
avec une marque d'ordre des octets, que PowerShell reconnaît. C'est le détour par un
fichier tiers qui perdait l'encodage — un quatrième piège Windows, après les fins de
ligne, l'environnement des sous-processus et l'encodage des flux.
