"""
config.py — VideoCreatorAI Configuration
Loads API keys and settings from .env file, validates required values.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv


def _load_runtime_settings() -> None:
    """Load .env and fallback Claude Code/OpenRouter settings from the workspace."""
    _env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=_env_path)

    settings_path = Path(__file__).resolve().parents[1] / ".claude" / "settings.local.json"
    if not settings_path.exists():
        return

    try:
        with settings_path.open("r", encoding="utf-8") as handle:
            settings = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return

    for key, value in settings.get("env", {}).items():
        os.environ[key] = str(value)


_load_runtime_settings()

# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------
NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY: str = os.getenv("PIXABAY_API_KEY", "")
LLM_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
LLM_API_BASE: str = os.getenv("ANTHROPIC_BASE_URL", os.getenv("OPENROUTER_BASE_URL", "http://127.0.0.1:4000"))
OPENROUTER_API_KEY: str = LLM_API_KEY
OPENROUTER_BASE_URL: str = LLM_API_BASE
LLM_MODEL: str = os.getenv("LLM_MODEL", os.getenv("OPENROUTER_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"))
LLM_MAX_TOKENS: int = min(8192, max(64, int(os.getenv("LLM_MAX_TOKENS", "2048"))))
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_REQUEST_TIMEOUT: int = int(os.getenv("LLM_REQUEST_TIMEOUT", "60"))
LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))

# ---------------------------------------------------------------------------
# NVIDIA NIM settings
# ---------------------------------------------------------------------------
NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL: str = "nvidia/llama-3.1-nemotron-ultra-253b-v1"
NVIDIA_MAX_TOKENS: int = 4096
NVIDIA_TEMPERATURE: float = 0.7
NVIDIA_REQUEST_TIMEOUT: int = 120   # seconds
NVIDIA_MAX_RETRIES: int = 3

# ---------------------------------------------------------------------------
# ElevenLabs settings
# ---------------------------------------------------------------------------
ELEVENLABS_MODEL_ID: str = "eleven_turbo_v2_5"
ELEVENLABS_STABILITY: float = 0.65
ELEVENLABS_SIMILARITY_BOOST: float = 0.85
ELEVENLABS_STYLE: float = 0.35
ELEVENLABS_USE_SPEAKER_BOOST: bool = True

# Recommended American narrator voices (from ElevenLabs voice library)
# Adam: deep, authoritative narrator
# Josh: warm, conversational
# Daniel: calm, professional
# Leave ELEVENLABS_VOICE_ID blank to auto-select first available

# ---------------------------------------------------------------------------
# Video settings
# ---------------------------------------------------------------------------
SEGMENT_DURATION: int = 5          # seconds per segment
VIDEO_FPS: int = 30
VIDEO_WIDTH: int = 1920
VIDEO_HEIGHT: int = 1080
VIDEO_CODEC: str = "libx264"
AUDIO_CODEC: str = "aac"

# ---------------------------------------------------------------------------
# Content settings
# ---------------------------------------------------------------------------
CONTENT_LANGUAGE: str = "en"       # Target language for scripts (en = English)

# ---------------------------------------------------------------------------
# Whisper transcription settings
# ---------------------------------------------------------------------------
WHISPER_MODEL: str = "whisper-1"   # OpenAI Whisper model

# ---------------------------------------------------------------------------
# Ken Burns effect settings (FFmpeg)
# ---------------------------------------------------------------------------
KEN_BURNS_ZOOM_FACTOR: float = 1.08
KEN_BURNS_PAN_SPEED: float = 0.001

# ---------------------------------------------------------------------------
# Subtitle styling (ASS format)
# ---------------------------------------------------------------------------
SUBTITLE_FONT: str = "Arial Black"
SUBTITLE_FONT_SIZE: int = 72
SUBTITLE_PRIMARY_COLOR: str = "&H00FFFF&"  # Yellow/gold in ASS BGR format
SUBTITLE_OUTLINE_COLOR: str = "&H000000&"  # Black outline
SUBTITLE_OUTLINE_WIDTH: int = 3
SUBTITLE_MARGIN_V: int = 120  # Distance from bottom

# ---------------------------------------------------------------------------
# Paths (relative to this file's directory)
# ---------------------------------------------------------------------------
_base = Path(__file__).parent
MEDIA_DIR: Path = Path(os.getenv("MEDIA_DIR", str(_base / "media")))
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", str(_base / "output")))
SCRIPT_PATH: Path = _base / "script.json"
VISUAL_PROMPTS_PATH: Path = _base / "visual_prompts.txt"
VOICEOVER_PATH: Path = _base / "voiceover.mp3"
OUTPUT_VIDEO_PATH: Path = OUTPUT_DIR / "output.mp4"
TIMESTAMPS_PATH: Path = _base / "timestamps.json"
SUBTITLES_PATH: Path = _base / "subtitles.ass"

# ---------------------------------------------------------------------------
# Supported media extensions
# ---------------------------------------------------------------------------
IMAGE_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTENSIONS: set = {".mp4", ".mov", ".webm", ".avi", ".mkv"}


def validate_config(require_nvidia: bool = False, require_elevenlabs: bool = True, require_openai: bool = False, require_pexels: bool = False) -> None:
    """
    Validate that the required API keys are present.
    Raises EnvironmentError with a clear message if any key is missing.
    """
    errors: list[str] = []

    if not OPENROUTER_API_KEY:
        errors.append(
            "OpenRouter API key is not set. "
            "Set ANTHROPIC_API_KEY or OPENROUTER_API_KEY in your environment or Claude settings."
        )

    if require_elevenlabs and not ELEVENLABS_API_KEY:
        errors.append(
            "ELEVENLABS_API_KEY is not set. "
            "Get your key at https://elevenlabs.io/ "
            "and add it to your .env file."
        )

    if require_openai and not OPENAI_API_KEY:
        errors.append(
            "OPENAI_API_KEY is not set. "
            "Get your key at https://platform.openai.com/api-keys "
            "and add it to your .env file."
        )

    if require_pexels and not PEXELS_API_KEY:
        errors.append(
            "PEXELS_API_KEY is not set. "
            "Get your key at https://www.pexels.com/api/ "
            "and add it to your .env file."
        )

    if errors:
        msg = "\n".join(f"  ❌ {e}" for e in errors)
        raise EnvironmentError(
            f"\nMissing API configuration:\n{msg}\n\n"
            f"Copy .env.template → .env and fill in the missing values."
        )


def ensure_dirs() -> None:
    """Create output and media directories if they don't exist."""
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
