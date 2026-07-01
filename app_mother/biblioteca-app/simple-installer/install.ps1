<#
    Registru Digital Biblioteca - Instalator simplu (un singur click)
    -----------------------------------------------------------------
    Ce face:
      1. Creeaza folderul aplicatiei in %LOCALAPPDATA%\RegistruDigital (fara drepturi de administrator)
      2. Descarca un Python "embeddable" izolat (nu atinge Python-ul din sistem)
      3. Descarca aplicatia din GitHub (sau o copiaza dintr-o sursa locala cu -AppSource)
      4. Instaleaza automat toate dependentele (PyQt6, SQLAlchemy, openpyxl, python-docx, reportlab)
      5. Creeaza o scurtatura pe Desktop si in Meniul Start
      6. Porneste aplicatia

    Pentru utilizatorul final: se ruleaza pur si simplu Install-RegistruDigital.exe.
    Acest fisier .ps1 este "creierul" din spatele acelui .exe.

    Parametri (pentru testare / instalare avansata):
      -InstallRoot <cale>   Suprascrie folderul de instalare
      -AppSource   <cale>   Foloseste o copie locala a folderului biblioteca-app in loc de descarcare
      -NoShortcut           Nu crea scurtaturi
      -NoLaunch             Nu porni aplicatia la final
#>

[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'RegistruDigital'),
    [string]$AppSource   = '',
    [switch]$NoShortcut,
    [switch]$NoLaunch
)

# ---------------------------------------------------------------------------
# Configurare
# ---------------------------------------------------------------------------
$ErrorActionPreference = 'Stop'
$ProgressPreference     = 'SilentlyContinue'   # accelereaza mult descarcarile in PowerShell 5.1

$AppName       = 'Registru Digital Biblioteca'
$ShortcutName  = 'Registru Digital'
$PyVersion     = '3.12.7'
$PyEmbedUrl    = "https://www.python.org/ftp/python/$PyVersion/python-$PyVersion-embed-amd64.zip"
$GetPipUrl     = 'https://bootstrap.pypa.io/get-pip.py'
$RepoZipUrl    = 'https://github.com/vicuvi1/mother_app_registru/archive/refs/heads/main.zip'

# Fisierele aplicatiei sunt incluse (bundle) direct in acest instalator, sub forma de
# arhiva ZIP codificata base64. Linia de mai jos este inlocuita automat de build-setup-exe.ps1.
$AppPayloadB64 = ''   # <-- APP_PAYLOAD: inlocuit de build-setup-exe.ps1

try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

# ---------------------------------------------------------------------------
# Ajutoare de afisare
# ---------------------------------------------------------------------------
function Write-Head($text) {
    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ''
}
function Write-Step($n, $total, $text) { Write-Host ("[{0}/{1}] {2}" -f $n, $total, $text) -ForegroundColor Green }
function Write-Info($text)             { Write-Host "      $text" -ForegroundColor Gray }
function Pause-End($text) { try { Read-Host $text | Out-Null } catch {} }
function Fail($text) {
    Write-Host ''
    Write-Host '------------------------------------------------------------' -ForegroundColor Red
    Write-Host "  EROARE: $text" -ForegroundColor Red
    Write-Host '------------------------------------------------------------' -ForegroundColor Red
    Write-Host ''
    Write-Host 'Verificati conexiunea la internet si incercati din nou.' -ForegroundColor Yellow
    Write-Host ''
    Pause-End 'Apasati Enter pentru a inchide'
    exit 1
}

$TOTAL = 6

# ---------------------------------------------------------------------------
Write-Head "Instalare $AppName"
Write-Host "  Aplicatia se va instala in:" -ForegroundColor White
Write-Host "  $InstallRoot" -ForegroundColor White
Write-Host ''
Write-Host '  Nu sunt necesare drepturi de administrator.' -ForegroundColor Gray
Write-Host '  Prima instalare dureaza cateva minute (se descarca ~60 MB).' -ForegroundColor Gray

$WorkTmp = Join-Path ([System.IO.Path]::GetTempPath()) ("RegistruSetup_" + [System.Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $WorkTmp | Out-Null

try {
    # -----------------------------------------------------------------------
    # 1. Pregatire folder de instalare (pastreaza datele existente la re-instalare)
    # -----------------------------------------------------------------------
    Write-Step 1 $TOTAL 'Pregatire folder de instalare...'
    $dataBackup = $null
    $existingData = Join-Path $InstallRoot 'app\data'
    if (Test-Path $existingData) {
        Write-Info 'Se pastreaza datele existente (baza de date + backup-uri)...'
        $dataBackup = Join-Path $WorkTmp 'data_backup'
        Copy-Item -Path $existingData -Destination $dataBackup -Recurse -Force
    }
    if (Test-Path (Join-Path $InstallRoot 'app')) {
        Remove-Item -Path (Join-Path $InstallRoot 'app') -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

    # -----------------------------------------------------------------------
    # 2. Python izolat (embeddable) + pip
    # -----------------------------------------------------------------------
    $pyDir = Join-Path $InstallRoot 'python'
    $pyExe = Join-Path $pyDir 'python.exe'
    if (-not (Test-Path $pyExe)) {
        Write-Step 2 $TOTAL "Descarcare Python $PyVersion (mediu izolat)..."
        $pyZip = Join-Path $WorkTmp 'python-embed.zip'
        try { Invoke-WebRequest -Uri $PyEmbedUrl -OutFile $pyZip -UseBasicParsing }
        catch { Fail "Nu s-a putut descarca Python de la python.org. $($_.Exception.Message)" }

        Write-Info 'Se dezarhiveaza Python...'
        if (Test-Path $pyDir) { Remove-Item $pyDir -Recurse -Force }
        Expand-Archive -Path $pyZip -DestinationPath $pyDir -Force

        # Activeaza site-packages in fisierul ._pth (necesar pentru pip / import module)
        $pth = Get-ChildItem -Path $pyDir -Filter 'python*._pth' | Select-Object -First 1
        if ($pth) {
            $stem = [System.IO.Path]::GetFileNameWithoutExtension($pth.Name)  # ex: python312
            @(
                "$stem.zip"
                '.'
                'Lib\site-packages'
                'import site'
            ) | Set-Content -Path $pth.FullName -Encoding ASCII
        }

        Write-Info 'Se instaleaza pip...'
        $getPip = Join-Path $WorkTmp 'get-pip.py'
        try { Invoke-WebRequest -Uri $GetPipUrl -OutFile $getPip -UseBasicParsing }
        catch { Fail "Nu s-a putut descarca instalatorul pip. $($_.Exception.Message)" }
        & $pyExe $getPip --no-warn-script-location --quiet
        if ($LASTEXITCODE -ne 0) { Fail 'Instalarea pip a esuat.' }
    } else {
        Write-Step 2 $TOTAL 'Python izolat exista deja - se reutilizeaza.'
    }

    # -----------------------------------------------------------------------
    # 3. Aplicatia (din GitHub sau dintr-o sursa locala)
    # -----------------------------------------------------------------------
    Write-Step 3 $TOTAL 'Obtinere aplicatie...'
    if ($AppSource -and (Test-Path $AppSource)) {
        Write-Info "Sursa locala: $AppSource"
        $bibDir = Get-Item $AppSource
    } elseif ($AppPayloadB64) {
        Write-Info 'Se extrage aplicatia inclusa in instalator...'
        $appZip = Join-Path $WorkTmp 'bundled-app.zip'
        [System.IO.File]::WriteAllBytes($appZip, [System.Convert]::FromBase64String($AppPayloadB64))
        $exDir = Join-Path $WorkTmp 'bundled'
        Expand-Archive -Path $appZip -DestinationPath $exDir -Force
        $bibDir = Get-Item $exDir
    } else {
        Write-Info 'Se descarca ultima versiune din GitHub...'
        $repoZip = Join-Path $WorkTmp 'app.zip'
        try { Invoke-WebRequest -Uri $RepoZipUrl -OutFile $repoZip -UseBasicParsing }
        catch { Fail "Nu s-a putut descarca aplicatia din GitHub. $($_.Exception.Message)" }
        $repoDir = Join-Path $WorkTmp 'repo'
        Expand-Archive -Path $repoZip -DestinationPath $repoDir -Force
        $bibDir = Get-ChildItem -Path $repoDir -Recurse -Directory -Filter 'biblioteca-app' | Select-Object -First 1
        if (-not $bibDir) { Fail 'Structura arhivei descarcate este neasteptata (lipseste biblioteca-app).' }
    }

    $srcApp = Join-Path $bibDir.FullName 'app'
    if (-not (Test-Path (Join-Path $srcApp 'main.py'))) { Fail 'Nu s-a gasit app\main.py in sursa aplicatiei.' }

    Write-Info 'Se copiaza fisierele aplicatiei...'
    Copy-Item -Path $srcApp -Destination (Join-Path $InstallRoot 'app') -Recurse -Force
    foreach ($f in @('requirements-runtime.txt', 'requirements.txt')) {
        $rf = Join-Path $bibDir.FullName $f
        if (Test-Path $rf) { Copy-Item $rf (Join-Path $InstallRoot $f) -Force }
    }

    # Restaureaza datele pastrate
    if ($dataBackup -and (Test-Path $dataBackup)) {
        $destData = Join-Path $InstallRoot 'app\data'
        if (Test-Path $destData) { Remove-Item $destData -Recurse -Force }
        Copy-Item -Path $dataBackup -Destination $destData -Recurse -Force
    }

    # -----------------------------------------------------------------------
    # 4. Instalare dependente
    # -----------------------------------------------------------------------
    Write-Step 4 $TOTAL 'Instalare dependente (PyQt6, export Excel/Word/PDF)...'
    Write-Info 'Aceasta este partea care dureaza cel mai mult, va rugam asteptati...'
    $reqFile = Join-Path $InstallRoot 'requirements-runtime.txt'
    if (-not (Test-Path $reqFile)) {
        # Plasa de siguranta daca fisierul lipseste din sursa
        @('PyQt6>=6.6,<7','SQLAlchemy>=2.0,<3','openpyxl>=3.1','python-docx>=1.1','reportlab>=4.0') |
            Set-Content -Path $reqFile -Encoding ASCII
    }
    & $pyExe -m pip install --no-warn-script-location -r $reqFile
    if ($LASTEXITCODE -ne 0) { Fail 'Instalarea dependentelor a esuat.' }

    # -----------------------------------------------------------------------
    # 5. Scurtaturi (Desktop + Meniul Start) + dezinstalator
    # -----------------------------------------------------------------------
    $pywExe   = Join-Path $pyDir 'pythonw.exe'
    $mainPy   = Join-Path $InstallRoot 'app\main.py'
    $iconPath = Join-Path $InstallRoot 'app\resources\registru.ico'
    if (-not (Test-Path $iconPath)) { $iconPath = $pywExe }

    if (-not $NoShortcut) {
        Write-Step 5 $TOTAL 'Creare scurtaturi...'
        $ws = New-Object -ComObject WScript.Shell

        function New-Lnk($path, $target, $arguments, $workdir, $icon, $desc) {
            $lnk = $ws.CreateShortcut($path)
            $lnk.TargetPath       = $target
            $lnk.Arguments        = $arguments
            $lnk.WorkingDirectory = $workdir
            $lnk.IconLocation     = $icon
            $lnk.Description       = $desc
            $lnk.Save()
        }

        $desktop  = [Environment]::GetFolderPath('Desktop')
        $programs = [Environment]::GetFolderPath('Programs')
        $startDir = Join-Path $programs $ShortcutName
        New-Item -ItemType Directory -Force -Path $startDir | Out-Null

        $appArgs = ('"{0}"' -f $mainPy)
        New-Lnk (Join-Path $desktop  "$ShortcutName.lnk") $pywExe $appArgs $InstallRoot $iconPath $AppName
        New-Lnk (Join-Path $startDir "$ShortcutName.lnk") $pywExe $appArgs $InstallRoot $iconPath $AppName

        # Dezinstalator
        $uninSrc = Join-Path $PSScriptRoot 'uninstall.ps1'
        $uninDst = Join-Path $InstallRoot 'uninstall.ps1'
        if (Test-Path $uninSrc) { Copy-Item $uninSrc $uninDst -Force }
        if (Test-Path $uninDst) {
            $psExe   = Join-Path $PSHOME 'powershell.exe'
            $uninArg = ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $uninDst)
            New-Lnk (Join-Path $startDir "Dezinstalare $ShortcutName.lnk") $psExe $uninArg $InstallRoot $iconPath "Dezinstalare $AppName"
        }
    } else {
        Write-Step 5 $TOTAL 'Scurtaturi omise (-NoShortcut).'
    }

    # -----------------------------------------------------------------------
    # 6. Gata + pornire
    # -----------------------------------------------------------------------
    Write-Step 6 $TOTAL 'Finalizare...'
    Write-Head 'Instalare finalizata cu succes!'
    Write-Host "  Aplicatia a fost instalata in:" -ForegroundColor White
    Write-Host "  $InstallRoot" -ForegroundColor White
    Write-Host ''
    if (-not $NoShortcut) {
        Write-Host '  Porniti aplicatia de pe scurtatura "Registru Digital" de pe Desktop.' -ForegroundColor White
    }
    Write-Host ''

    if (-not $NoLaunch) {
        Write-Host '  Se porneste aplicatia...' -ForegroundColor Green
        Start-Process -FilePath $pywExe -ArgumentList ('"{0}"' -f $mainPy) -WorkingDirectory $InstallRoot | Out-Null
        Start-Sleep -Seconds 2
    } else {
        Pause-End 'Apasati Enter pentru a inchide'
    }
}
finally {
    if (Test-Path $WorkTmp) { Remove-Item $WorkTmp -Recurse -Force -ErrorAction SilentlyContinue }
}
