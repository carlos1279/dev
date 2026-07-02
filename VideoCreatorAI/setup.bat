@echo off
REM ============================================================
REM VideoCreatorAI — Windows Setup Script
REM Run this once to install Python, create a venv, and install
REM all required packages.
REM ============================================================

echo.
echo  ==========================================
echo   VideoCreatorAI ^| Setup
echo  ==========================================
echo.

REM ── Step 1: Check for Python ──────────────────────────────
where python >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo [OK] Python found.
    python --version
    GOTO :CREATE_VENV
)

echo [INFO] Python not found. Downloading Python 3.11 installer...
echo.

REM ── Step 2: Download Python installer ─────────────────────
set PYTHON_INSTALLER=%TEMP%\python-3.11.9-amd64.exe
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%PYTHON_INSTALLER%'"

IF NOT EXIST "%PYTHON_INSTALLER%" (
    echo [ERROR] Download failed. Please install Python manually from https://python.org
    pause
    exit /b 1
)

REM ── Step 3: Install Python silently ───────────────────────
echo [INFO] Installing Python 3.11 silently (this may take a minute)...
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1

REM Refresh PATH
set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

echo [OK] Python installed.

:CREATE_VENV
REM ── Step 4: Create virtual environment ────────────────────
echo.
echo [INFO] Creating virtual environment...
python -m venv venv

IF NOT EXIST "venv\Scripts\activate.bat" (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo [OK] Virtual environment created.

REM ── Step 5: Activate and install dependencies ─────────────
echo.
echo [INFO] Installing dependencies (this may take a few minutes)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt

echo.
echo  ==========================================
echo   Setup complete!
echo  ==========================================
echo.
echo  Next steps:
echo    1. Copy .env.template to .env
echo    2. Fill in your NVIDIA_API_KEY and ELEVENLABS_API_KEY
echo    3. Run:  venv\Scripts\activate   ^&^&   python main.py
echo.
pause
