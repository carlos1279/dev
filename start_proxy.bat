@echo off
REM ============================================================
REM LiteLLM Proxy — Avvia PRIMA di usare Claude Code
REM Converte le chiamate Anthropic in formato OpenAI per Groq
REM ============================================================

set PYTHONIOENCODING=utf-8

echo [LiteLLM] Avvio proxy su http://localhost:4000 ...
echo [LiteLLM] Premi CTRL+C per fermare il proxy
echo.

"C:\pye\Scripts\litellm.exe" --config litellm_config.yaml --port 4000 --host 127.0.0.1
pause
