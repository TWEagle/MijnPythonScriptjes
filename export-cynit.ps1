param(
    [string]$RootDir   = "C:\gh\MijnPythonScriptjes",
    [string]$OutDir    = "$PSScriptRoot\dist",
    [string]$BundleName = "cynit_bundle"
)

$ErrorActionPreference = "Stop"

$cyNitDir = Join-Path $RootDir "CyNiT-tools"
$spytDir  = Join-Path $RootDir "SP-YT"

if (!(Test-Path $cyNitDir)) { throw "CyNiT-tools map niet gevonden: $cyNitDir" }
if (!(Test-Path $spytDir))  { throw "SP-YT map niet gevonden: $spytDir" }

# Staging map
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$bundleFolderName = "${BundleName}_$timestamp"
$staging = Join-Path $env:TEMP $bundleFolderName

if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Path $staging | Out-Null

Write-Host "Copy CyNiT-tools..."
Copy-Item $cyNitDir (Join-Path $staging "CyNiT-tools") -Recurse -Force `
    -Exclude "venv","*.log","__pycache__",".git",".venv",".mypy_cache"

Write-Host "Copy SP-YT..."
Copy-Item $spytDir (Join-Path $staging "SP-YT") -Recurse -Force `
    -Exclude "venv","*.log","__pycache__",".git",".venv",".mypy_cache"

# Requirements genereren (optioneel, maar handig)
Write-Host "Generate requirements_cynit.txt..."
Push-Location $cyNitDir
python -m pip freeze | Set-Content (Join-Path $staging "requirements_cynit.txt")
Pop-Location

Write-Host "Generate requirements_spyt.txt..."
Push-Location $spytDir
python -m pip freeze | Set-Content (Join-Path $staging "requirements_spyt.txt")
Pop-Location

# Dist map
if (!(Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }

$zipPath = Join-Path $OutDir "$bundleFolderName.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

Write-Host "Create archive: $zipPath"
Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zipPath

Write-Host "Ready: $zipPath"
