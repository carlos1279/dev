@echo off
setlocal
cd /d "%~dp0"

set "ANTHROPIC_AUTH_TOKEN="
set "ANTHROPIC_API_KEY=sk-fake-key-for-claude-code"
set "ANTHROPIC_BASE_URL=http://127.0.0.1:4000"
set "ANTHROPIC_MODEL=claude-3-5-sonnet-latest"
set "LLM_MODEL=llama-3.3-70b-versatile"
set "LITELLM_CONFIG=litellm_config.yaml"
set "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1"

where claude >nul 2>nul
if errorlevel 1 (
    echo Claude CLI not found on PATH.
    exit /b 1
)

claude
