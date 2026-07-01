<#
    Registru Digital Biblioteca - Dezinstalare
    Sterge scurtaturile si folderul aplicatiei din %LOCALAPPDATA%\RegistruDigital.
    NU necesita drepturi de administrator.
#>
[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'RegistruDigital'),
    [switch]$KeepData
)

$ShortcutName = 'Registru Digital'

Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host '  Dezinstalare Registru Digital Biblioteca' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ''

$answer = Read-Host 'Sigur doriti sa dezinstalati aplicatia? (D/N)'
if ($answer -notmatch '^[DdYy]') {
    Write-Host 'Dezinstalare anulata.' -ForegroundColor Yellow
    Start-Sleep -Seconds 1
    exit 0
}

# 1. Scurtaturi
$desktop  = [Environment]::GetFolderPath('Desktop')
$programs = [Environment]::GetFolderPath('Programs')
$targets  = @(
    (Join-Path $desktop  "$ShortcutName.lnk")
    (Join-Path $programs $ShortcutName)
)
foreach ($t in $targets) {
    if (Test-Path $t) {
        Remove-Item $t -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Sters: $t" -ForegroundColor Gray
    }
}

# 2. Optional: pastreaza datele utilizatorului
if ($KeepData) {
    $data = Join-Path $InstallRoot 'app\data'
    if (Test-Path $data) {
        $backup = Join-Path ([Environment]::GetFolderPath('Desktop')) 'RegistruDigital_Date_Salvate'
        Copy-Item $data $backup -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Datele au fost copiate pe Desktop in: $backup" -ForegroundColor Green
    }
}

# 3. Folderul aplicatiei (nu ne stergem singuri fisierul care ruleaza -> copiem intr-un temp)
if (Test-Path $InstallRoot) {
    try {
        Remove-Item $InstallRoot -Recurse -Force
        Write-Host "Sters: $InstallRoot" -ForegroundColor Gray
    } catch {
        Write-Host "Nu s-a putut sterge complet $InstallRoot (poate aplicatia inca ruleaza)." -ForegroundColor Yellow
        Write-Host 'Inchideti aplicatia si stergeti manual folderul.' -ForegroundColor Yellow
    }
}

Write-Host ''
Write-Host 'Dezinstalare finalizata.' -ForegroundColor Green
Start-Sleep -Seconds 2
