<#
    Compileaza install.ps1 intr-un singur fisier executabil: Install-RegistruDigital.exe
    -----------------------------------------------------------------------------------
    Pasii:
      1. Impacheteaza folderul aplicatiei (app\ + requirements-runtime.txt) intr-un ZIP
      2. Codifica ZIP-ul in base64 si il insereaza in install.ps1 (aplicatia devine "inclusa")
      3. Compileaza scriptul rezultat intr-un singur .exe cu ps2exe

    Ruleaza acest script O SINGURA DATA, pe masina ta de dezvoltare, pentru a regenera
    fisierul .exe dupa ce ai modificat aplicatia.

    Utilizare:
        powershell -ExecutionPolicy Bypass -File build-setup-exe.ps1

    Necesita modulul "ps2exe" (se instaleaza automat din PowerShell Gallery daca lipseste).
#>
[CmdletBinding()]
param(
    [string]$OutFile = (Join-Path $PSScriptRoot 'Install-RegistruDigital.exe')
)

$ErrorActionPreference = 'Stop'
$here    = $PSScriptRoot
$appRoot = (Resolve-Path (Join-Path $here '..')).Path   # ...\biblioteca-app
$src     = Join-Path $here 'install.ps1'
$icon    = Join-Path $here 'registru.ico'

# ---------------------------------------------------------------------------
# 1. Impacheteaza aplicatia (app\ fara folderul data, + requirements-runtime.txt)
# ---------------------------------------------------------------------------
Write-Host '[1/3] Impachetare fisiere aplicatie...' -ForegroundColor Cyan
$stage = Join-Path $env:TEMP ("RegistruBundle_" + [System.Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $stage | Out-Null
try {
    # copiaza app\ fara datele de utilizator
    $stageApp = Join-Path $stage 'app'
    Copy-Item (Join-Path $appRoot 'app') $stageApp -Recurse -Force
    $stageData = Join-Path $stageApp 'data'
    if (Test-Path $stageData) { Remove-Item $stageData -Recurse -Force }

    foreach ($f in @('requirements-runtime.txt', 'requirements.txt')) {
        $rf = Join-Path $appRoot $f
        if (Test-Path $rf) { Copy-Item $rf (Join-Path $stage $f) -Force }
    }

    $zip = Join-Path $env:TEMP ("RegistruBundle_" + [System.Guid]::NewGuid().ToString('N') + '.zip')
    if (Test-Path $zip) { Remove-Item $zip -Force }
    Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -Force

    $bytes = [System.IO.File]::ReadAllBytes($zip)
    $b64   = [System.Convert]::ToBase64String($bytes)
    $mb    = [math]::Round($bytes.Length / 1MB, 2)
    Write-Host "      Aplicatie impachetata: $mb MB" -ForegroundColor Gray
    Remove-Item $zip -Force
}
finally {
    if (Test-Path $stage) { Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue }
}

# ---------------------------------------------------------------------------
# 2. Insereaza payload-ul in install.ps1 -> script combinat temporar
# ---------------------------------------------------------------------------
Write-Host '[2/3] Inserare aplicatie in scriptul instalatorului...' -ForegroundColor Cyan
$lines  = Get-Content -Path $src -Encoding UTF8
$marker = '# <-- APP_PAYLOAD: inlocuit de build-setup-exe.ps1'
$found  = $false
$out    = foreach ($ln in $lines) {
    if ($ln -match [regex]::Escape($marker)) {
        $found = $true
        "`$AppPayloadB64 = '$b64'"
    } else {
        $ln
    }
}
if (-not $found) { throw "Nu s-a gasit marcajul APP_PAYLOAD in install.ps1." }

$combined = Join-Path $env:TEMP ("install_combined_" + [System.Guid]::NewGuid().ToString('N') + '.ps1')
Set-Content -Path $combined -Value $out -Encoding UTF8

# ---------------------------------------------------------------------------
# 3. Compileaza cu ps2exe
# ---------------------------------------------------------------------------
Write-Host '[3/3] Compilare .exe cu ps2exe...' -ForegroundColor Cyan
if (-not (Get-Module -ListAvailable -Name ps2exe)) {
    Write-Host '      Se instaleaza ps2exe din PowerShell Gallery...' -ForegroundColor Yellow
    try { Install-PackageProvider -Name NuGet -Force -Scope CurrentUser | Out-Null } catch {}
    try { Set-PSRepository -Name PSGallery -InstallationPolicy Trusted } catch {}
    Install-Module -Name ps2exe -Scope CurrentUser -Force
}
Import-Module ps2exe -Force

try {
    $params = @{
        inputFile    = $combined
        outputFile   = $OutFile
        title        = 'Instalare Registru Digital'
        product      = 'Registru Digital Biblioteca'
        description  = 'Instalator Registru Digital Biblioteca'
        company      = 'Biblioteca'
        version      = '1.7.0.0'
        requireAdmin = $false
    }
    if (Test-Path $icon) { $params['iconFile'] = $icon }
    Invoke-ps2exe @params
}
finally {
    if (Test-Path $combined) { Remove-Item $combined -Force -ErrorAction SilentlyContinue }
}

if (Test-Path $OutFile) {
    $sizeMb = [math]::Round((Get-Item $OutFile).Length / 1MB, 2)
    Write-Host ''
    Write-Host "GATA! Executabil creat ($sizeMb MB):" -ForegroundColor Green
    Write-Host "  $OutFile" -ForegroundColor White
    Write-Host ''
    Write-Host 'Distribuie acest fisier utilizatorilor. Ei doar dau dublu-click pe el.' -ForegroundColor Green
} else {
    throw 'Compilarea a esuat - fisierul .exe nu a fost creat.'
}
