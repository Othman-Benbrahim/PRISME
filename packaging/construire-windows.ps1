#Requires -Version 5.1
[CmdletBinding()]
param([string]$Sortie = "")
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Racine = Split-Path -Parent $PSScriptRoot
if ($env:OS -ne "Windows_NT") { throw "Construction Windows uniquement." }
if (-not [Environment]::Is64BitOperatingSystem) { throw "Windows x64 est requis." }
foreach ($Outil in @("git", "py", "node", "npm.cmd")) {
    if (-not (Get-Command $Outil -ErrorAction SilentlyContinue)) { throw "Outil de construction absent : $Outil" }
}
$Atelier = Join-Path ([IO.Path]::GetTempPath()) ("PRISME-build-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $Atelier | Out-Null
if (-not $Sortie) { $Sortie = Join-Path $Racine ("dist\E9-" + [guid]::NewGuid().ToString("N").Substring(0,12)) }
$Sortie = [IO.Path]::GetFullPath($Sortie)
try {
    Push-Location $Racine
    try {
        & py -3.12 -c "import struct; assert struct.calcsize('P') == 8, 'Python x64 requis'"
        if ($LASTEXITCODE -ne 0) { throw "Installez Python 3.12 x64 pour construire l'application." }
        & node -e "if(Number(process.versions.node.split('.')[0])<22)process.exit(1)"
        if ($LASTEXITCODE -ne 0) { throw "Node.js 22 ou plus récent est requis pour les tests Constat." }
        & py -3.12 -m venv (Join-Path $Atelier "venv")
        if ($LASTEXITCODE -ne 0) { throw "Création du venv impossible." }
        $Python = Join-Path $Atelier "venv\Scripts\python.exe"
        & $Python -X utf8 -m pip install --disable-pip-version-check -r packaging/requirements-build.txt
        if ($LASTEXITCODE -ne 0) { throw "Installation des dépendances de construction impossible." }
        & $Python -X utf8 -m pip check
        if ($LASTEXITCODE -ne 0) { throw "Dépendances incompatibles." }
        & $Python -X utf8 -m unittest discover -s tests
        if ($LASTEXITCODE -ne 0) { throw "Tests Python échoués : aucune archive de release créée." }
        & npm.cmd ci --prefix plugins/constat
        if ($LASTEXITCODE -ne 0) { throw "Installation des dépendances de test Constat impossible." }
        & npm.cmd test --prefix plugins/constat
        if ($LASTEXITCODE -ne 0) { throw "Tests Constat échoués : aucune archive de release créée." }
        & $Python -X utf8 packaging/construire.py --sortie $Sortie
        if ($LASTEXITCODE -ne 0) { throw "Construction ou contrôle du binaire échoué." }
        Write-Host "Archive et empreintes : $Sortie"
        Write-Host "Vérification visuelle : docs/branches/e9-publication.md"
    } finally { Pop-Location }
} finally {
    Write-Host "Environnement de construction conservé : $Atelier"
}
