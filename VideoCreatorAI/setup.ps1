# ============================================================
# VideoCreatorAI — PowerShell Setup Script (alternative)
# Run from PowerShell:  .\setup.ps1
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "   VideoCreatorAI | Setup" -ForegroundColor Cyan
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""

# ── Helper: find a working Python executable ──────────────────────────────
function Find-Python {
    $candidates = @(
        "python",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Python311\python.exe",
        "C:\Python312\python.exe"
    )
    foreach ($cmd in $candidates) {
        try {
            $ver = & $cmd --version 2>&1
            if ($ver -match "Python 3\.\d+") {
                return $cmd
            }
        } catch {}
    }
    return $null
}

# ── Step 1: Check for Python ──────────────────────────────────────────────
Write-Host "[1/4] Checking for Python..." -ForegroundColor Yellow
$pythonCmd = Find-Python

if (-not $pythonCmd) {
    Write-Host "      Python not found. Downloading Python 3.11.9..." -ForegroundColor Yellow

    $installerPath = "$env:TEMP\python-3.11.9-amd64.exe"
    $pythonUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"

    try {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath -UseBasicParsing
        Write-Host "      Installing Python 3.11 (silent)..." -ForegroundColor Yellow
        Start-Process -FilePath $installerPath -ArgumentList `
            "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_pip=1" `
            -Wait -NoNewWindow

        # Refresh environment path
        $env:PATH = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + `
                    [System.Environment]::GetEnvironmentVariable("Path", "Machine")

        $pythonCmd = Find-Python
        if (-not $pythonCmd) {
            throw "Python installation completed but executable not found. Please restart PowerShell."
        }
        Write-Host "  [OK] Python installed: $(& $pythonCmd --version)" -ForegroundColor Green
    } catch {
        Write-Host ""
        Write-Host "  [ERROR] Could not install Python automatically." -ForegroundColor Red
        Write-Host "  Please download and install Python 3.11+ from: https://python.org" -ForegroundColor Red
        Write-Host "  Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Red
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "  [OK] Found: $(& $pythonCmd --version)" -ForegroundColor Green
}

# ── Step 2: Create virtual environment ────────────────────────────────────
Write-Host ""
Write-Host "[2/4] Creating virtual environment..." -ForegroundColor Yellow
& $pythonCmd -m venv venv
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "  [ERROR] Failed to create virtual environment." -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Virtual environment created." -ForegroundColor Green

# ── Step 3: Install dependencies ──────────────────────────────────────────
Write-Host ""
Write-Host "[3/4] Installing dependencies (this may take a few minutes)..." -ForegroundColor Yellow
& "venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& "venv\Scripts\pip.exe" install -r requirements.txt

Write-Host "  [OK] All packages installed." -ForegroundColor Green

# ── Step 4: Copy .env template ────────────────────────────────────────────
Write-Host ""
Write-Host "[4/4] Setting up .env file..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.template" ".env"
    Write-Host "  [OK] .env created from template. Fill in your API keys!" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] .env already exists." -ForegroundColor DarkGray
}

# ── Done ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "   Setup complete!" -ForegroundColor Green
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "    1. Edit .env and add your API keys" -ForegroundColor White
Write-Host "    2. Run: .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "    3. Run: python main.py" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to exit"
