@echo off
REM ============================================================
REM VideoCreatorAI — Avvio rapido
REM Usa Python da C:\pye (installato senza admin)
REM ============================================================

cd /d "%~dp0"

if not exist "C:\pye\python.exe" (
    echo [ERRORE] Python non trovato in C:\pye
    echo Contatta il supporto o riesegui il setup.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [ERRORE] File .env mancante!
    echo Copia .env.template in .env e inserisci le tue API key.
    pause
    exit /b 1
)

echo [VideoCreatorAI] Avvio in corso...
"C:\pye\python.exe" main.py
pause
