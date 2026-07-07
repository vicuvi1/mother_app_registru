<#
    Registru Digital Biblioteca - Instalator simplu (un singur click)
    -----------------------------------------------------------------
    Ce face:
      1. Creeaza folderul aplicatiei in %LOCALAPPDATA%\RegistruDigital (fara drepturi de administrator)
      2. Descarca un Python "embeddable" izolat (nu atinge Python-ul din sistem)
      3. Descarca aplicatia din GitHub (sau o copiaza dintr-o sursa locala cu -AppSource)
      4. Instaleaza automat toate dependentele (PyQt5, SQLAlchemy, openpyxl, python-docx, reportlab)

    Windows 7: necesita SP1 + actualizarea "Universal C Runtime" (KB2999226).
    Fara ea, Python 3.8 nu porneste. Rulati Windows Update complet inainte.
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
# Windows 7: Python 3.8 (32-bit) — ultima serie Python care porneste pe Win7.
# 32-bit (win32) ruleaza atat pe Win7 pe 32 cat si pe 64 de biti.
$PyVersion     = '3.8.10'
$PyEmbedUrl    = "https://www.python.org/ftp/python/$PyVersion/python-$PyVersion-embed-win32.zip"
# get-pip fixat pe seria 3.8 (varianta generica cere Python 3.9+).
$GetPipUrl     = 'https://bootstrap.pypa.io/pip/3.8/get-pip.py'
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

        # Verificare Windows 7: fara UCRT (KB2999226) python.exe nu porneste.
        & $pyExe --version > $null 2>&1
        if ($LASTEXITCODE -ne 0) {
            Fail ("Python nu a putut porni. Pe Windows 7 este necesara actualizarea " +
                  "'Universal C Runtime' (KB2999226). Rulati Windows Update complet " +
                  "sau instalati KB2999226 de la Microsoft, apoi reincercati.")
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
    Write-Step 4 $TOTAL 'Instalare dependente (PyQt5, export Excel/Word/PDF)...'
    Write-Info 'Aceasta este partea care dureaza cel mai mult, va rugam asteptati...'
    $reqFile = Join-Path $InstallRoot 'requirements-runtime.txt'
    if (-not (Test-Path $reqFile)) {
        # Plasa de siguranta daca fisierul lipseste din sursa (versiuni compatibile Win7 / Python 3.8)
        @('PyQt5==5.15.10','SQLAlchemy>=2.0,<2.1','openpyxl>=3.1,<3.2','python-docx>=1.1,<1.2','reportlab>=4.0,<4.3') |
            Set-Content -Path $reqFile -Encoding ASCII
    }
    & $pyExe -m pip install --no-warn-script-location -r $reqFile
    if ($LASTEXITCODE -ne 0) { Fail 'Instalarea dependentelor a esuat.' }

    # Verificare PyQt5: pe Windows 7 bibliotecile Qt5 cer "Visual C++ 2015-2022
    # Redistributable (x86)". Daca lipseste, importul esueaza (ex: vcruntime140_1.dll).
    & $pyExe -c "from PyQt5.QtWidgets import QApplication" > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Fail ("PyQt5 nu a putut fi incarcat. Pe Windows 7 instalati 'Microsoft Visual C++ " +
              "2015-2022 Redistributable (x86)' de la Microsoft, apoi reincercati.")
    }

    # -----------------------------------------------------------------------
    # 5. Scurtaturi (Desktop + Meniul Start) + dezinstalator
    # -----------------------------------------------------------------------
    $pywExe   = Join-Path $pyDir 'pythonw.exe'
    $mainPy   = Join-Path $InstallRoot 'app\main.py'
    $iconPath = Join-Path $InstallRoot 'app\resources\registru.ico'
    if (-not (Test-Path $iconPath)) { $iconPath = $pywExe }

    if (-not $NoShortcut) {
        Write-Step 5 $TOTAL 'Creare scurtaturi...'
        # Scurtaturile nu sunt critice: daca ceva esueaza aici, aplicatia este deja
        # instalata, deci prindem eroarea si continuam (nu inchidem instalatorul).
        try {
            $ws = New-Object -ComObject WScript.Shell

            function New-Lnk($path, $target, $arguments, $workdir, $icon, $desc) {
                $lnk = $ws.CreateShortcut($path)
                $lnk.TargetPath       = $target
                $lnk.Arguments        = $arguments
                $lnk.WorkingDirectory = $workdir
                if ($icon) { $lnk.IconLocation = $icon }
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

            # Dezinstalator: scris direct in folderul aplicatiei. NU folosim $PSScriptRoot,
            # care este gol intr-un .exe compilat cu ps2exe (cauza inchiderii bruste anterioare).
            $uninDst = Join-Path $InstallRoot 'uninstall.ps1'
            Set-Content -Path $uninDst -Encoding UTF8 -Value @'
$root = Join-Path $env:LOCALAPPDATA 'RegistruDigital'
$name = 'Registru Digital'
Write-Host 'Dezinstalare Registru Digital Biblioteca...' -ForegroundColor Cyan
$a = Read-Host 'Sigur doriti sa dezinstalati aplicatia? (D/N)'
if ($a -notmatch '^[DdYy]') { Write-Host 'Anulat.'; Start-Sleep 1; exit }
$desk = [Environment]::GetFolderPath('Desktop')
$prog = [Environment]::GetFolderPath('Programs')
Remove-Item (Join-Path $desk "$name.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $prog $name) -Recurse -Force -ErrorAction SilentlyContinue
Get-Process pythonw, python -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith($root, [StringComparison]::OrdinalIgnoreCase) } |
    Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 1
try { Remove-Item $root -Recurse -Force -ErrorAction Stop; Write-Host 'Dezinstalare finalizata.' -ForegroundColor Green }
catch { Write-Host 'Inchideti aplicatia si stergeti manual folderul:' -ForegroundColor Yellow; Write-Host "  $root" }
Start-Sleep 2
'@
            $psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
            if ($PSHOME -and (Test-Path (Join-Path $PSHOME 'powershell.exe'))) { $psExe = Join-Path $PSHOME 'powershell.exe' }
            $uninArg = ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $uninDst)
            New-Lnk (Join-Path $startDir "Dezinstalare $ShortcutName.lnk") $psExe $uninArg $InstallRoot $iconPath "Dezinstalare $AppName"
        } catch {
            Write-Info ("Scurtaturile nu au putut fi create complet: " + $_.Exception.Message)
            Write-Info 'Aplicatia este totusi instalata si poate fi pornita.'
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
catch {
    # Prinde ORICE eroare neasteptata ca fereastra sa nu se inchida brusc, ci sa afiseze cauza.
    Write-Host ''
    Write-Host '------------------------------------------------------------' -ForegroundColor Red
    Write-Host '  Instalarea nu s-a putut finaliza.' -ForegroundColor Red
    Write-Host ("  " + $_.Exception.Message) -ForegroundColor Red
    if ($_.InvocationInfo) { Write-Host ("  (" + $_.InvocationInfo.PositionMessage + ")") -ForegroundColor DarkGray }
    Write-Host '------------------------------------------------------------' -ForegroundColor Red
    Write-Host ''
    Write-Host 'Trimiteti acest mesaj pentru asistenta.' -ForegroundColor Yellow
    Write-Host ''
    Pause-End 'Apasati Enter pentru a inchide'
    exit 1
}
finally {
    if (Test-Path $WorkTmp) { Remove-Item $WorkTmp -Recurse -Force -ErrorAction SilentlyContinue }
}
