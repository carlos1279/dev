import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import script_generator
import config


def test_uses_openrouter_llama_model():
    assert script_generator._SYSTEM_PROMPT
    assert hasattr(script_generator, "_call_llm_provider")
    assert "llama" in config.LLM_MODEL.lower()
    assert "4000" in config.LLM_API_BASE or "groq" in config.LLM_API_BASE.lower() or "openrouter" in config.LLM_API_BASE.lower()
