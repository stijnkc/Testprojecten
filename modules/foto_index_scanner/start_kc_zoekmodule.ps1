$ErrorActionPreference = 'Stop'
trap {
    Write-Host ""
    Write-Host "  =============================================" -ForegroundColor Red
    Write-Host "  ONVERWACHTE FOUT:" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  =============================================" -ForegroundColor Red
    Write-Host ""
    Read-Host "Druk op Enter om af te sluiten"
    exit 1
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Paden voor de lokale omgeving (eenmalig per laptop)
$VenvDir       = "$env:LOCALAPPDATA\KC_Zoekmodule\venv"
$VenvPython    = "$VenvDir\Scripts\python.exe"
$VenvStreamlit = "$VenvDir\Scripts\streamlit.exe"

# SNELPAD: omgeving bestaat al -> controleren en opstarten
if ((Test-Path $VenvStreamlit) -and (Test-Path $VenvPython)) {
    $testResult = & $VenvStreamlit --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Bestaande omgeving is beschadigd, opnieuw installeren..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $VenvDir -ErrorAction SilentlyContinue
    } else {
        Write-Host ""
        Write-Host "  KC Foto Archief Zoekmodule wordt gestart..." -ForegroundColor Green
        Write-Host "  Sluit dit venster NIET - dit stopt de server." -ForegroundColor DarkGray
        Write-Host ""
        & $VenvStreamlit run app.py --browser.gatherUsageStats=false
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "  Fout bij opstarten (code $LASTEXITCODE)." -ForegroundColor Red
            Read-Host "Druk op Enter om af te sluiten"
        }
        exit
    }
}

# EERSTE KEER: eenmalige installatie (ca. 1-2 minuten)
Write-Host ""
Write-Host "  +--------------------------------------------------+" -ForegroundColor Yellow
Write-Host "  |  Eerste keer opstarten - even geduld a.u.b.     |" -ForegroundColor Yellow
Write-Host "  |  Dit scherm verschijnt daarna NOOIT meer.        |" -ForegroundColor Yellow
Write-Host "  +--------------------------------------------------+" -ForegroundColor Yellow
Write-Host ""

# Stap 1: Zoek Python op dit systeem
$pythonExe = $null

# Controleer eerst de bekende installatiepaden (meest betrouwbaar)
foreach ($v in @("313","312","311","310","39")) {
    $c = "$env:LOCALAPPDATA\Programs\Python\Python$v\python.exe"
    if (Test-Path $c) { $pythonExe = $c; break }
}

# Daarna pas PATH doorzoeken — maar NIET de Windows Store-alias uitvoeren (die hangt)
if (-not $pythonExe) {
    $ErrorActionPreference = 'Continue'
    $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
    $ErrorActionPreference = 'Stop'
    if ($pythonCmd -and $pythonCmd.Source -notlike "*WindowsApps*") {
        # Echte Python gevonden in PATH, niet de Store-alias
        $pythonExe = $pythonCmd.Source
    }
}


# Python niet gevonden -> automatisch installeren
if (-not $pythonExe) {
    Write-Host "  [1/3] Python downloaden en installeren..." -ForegroundColor Cyan
    $installer = "$env:TEMP\python-3.11.5-amd64.exe"
    try {
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe" `
                          -OutFile $installer -UseBasicParsing
        Start-Process -FilePath $installer `
                      -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1" `
                      -Wait
        $pythonExe = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
        if (-not (Test-Path $pythonExe)) { throw "Python exe niet gevonden na installatie." }
        Write-Host "        Python geinstalleerd." -ForegroundColor Green
    } catch {
        Write-Host ""
        Write-Host "  FOUT: Python kon niet worden geinstalleerd." -ForegroundColor Red
        Write-Host "  Installeer Python via https://www.python.org/downloads/" -ForegroundColor Red
        Write-Host "  Foutmelding: $_" -ForegroundColor DarkRed
        Read-Host "Druk op Enter om af te sluiten"
        exit 1
    }
} else {
    Write-Host "  [1/3] Python gevonden." -ForegroundColor Green
}

# Stap 2: Maak lokale venv aan
Write-Host "  [2/3] Lokale omgeving aanmaken..." -ForegroundColor Cyan
$ErrorActionPreference = 'Continue'
& $pythonExe -m venv $VenvDir
$ErrorActionPreference = 'Stop'
if (-not (Test-Path $VenvPython)) {
    Write-Host "  FOUT: venv aanmaken mislukt." -ForegroundColor Red
    Read-Host "Druk op Enter om af te sluiten"
    exit 1
}
Write-Host "        Omgeving aangemaakt." -ForegroundColor Green

# Stap 3: Installeer pakketten (output zichtbaar zodat fouten leesbaar zijn)
Write-Host "  [3/3] Benodigde software installeren (dit duurt even)..." -ForegroundColor Cyan
$ErrorActionPreference = 'Continue'
& "$VenvDir\Scripts\pip.exe" install --upgrade pip
& "$VenvDir\Scripts\pip.exe" install streamlit pandas openpyxl pillow
$pipExit = $LASTEXITCODE
$ErrorActionPreference = 'Stop'
if ($pipExit -ne 0) {
    Write-Host ""
    Write-Host "  FOUT: pip install mislukt (exit $pipExit)." -ForegroundColor Red
    Write-Host "  Controleer je internetverbinding en probeer opnieuw." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $VenvDir -ErrorAction SilentlyContinue
    Read-Host "Druk op Enter om af te sluiten"
    exit 1
}
Write-Host "        Software geinstalleerd." -ForegroundColor Green

# Gereed -> opstarten
Write-Host ""
Write-Host "  Klaar! De zoekmodule wordt nu gestart in je browser." -ForegroundColor Green
Write-Host "  Sluit dit venster NIET - dit stopt de server." -ForegroundColor DarkGray
Write-Host ""
& $VenvStreamlit run app.py --browser.gatherUsageStats=false

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  Fout bij opstarten (code $LASTEXITCODE)." -ForegroundColor Red
    Read-Host "Druk op Enter om af te sluiten"
}
