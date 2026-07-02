"""
audio_generator.py — VideoCreatorAI Audio Generator

Reads the narration text from script.json, sends it to the ElevenLabs API
for text-to-speech conversion, and saves the result as voiceover.mp3.
"""

from __future__ import annotations

import time
from pathlib import Path

from elevenlabs import ElevenLabs, VoiceSettings

import config
from script_generator import VideoScript, load_script


# ---------------------------------------------------------------------------
# ElevenLabs character limit per request (free tier: 10 000 chars / month)
# We chunk at 5 000 chars to stay safely within per-request limits.
# ---------------------------------------------------------------------------
_CHUNK_SIZE: int = 5_000


def _get_client() -> ElevenLabs:
    """Return an authenticated ElevenLabs client."""
    return ElevenLabs(api_key=config.ELEVENLABS_API_KEY)


def _build_full_text(script: VideoScript) -> str:
    """Concatenate all segment texts into one narration string."""
    return " ".join(seg.text.strip() for seg in script.segments)


def _chunk_text(text: str, max_chars: int = _CHUNK_SIZE) -> list[str]:
    """
    Split text into chunks ≤ max_chars at sentence boundaries.
    Falls back to hard split if no sentence boundary is found.
    """
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= max_chars:
            chunks.append(text)
            break
        # Try to split at the last period/exclamation/question before the limit
        split_at = max_chars
        for delim in (".", "!", "?"):
            pos = text.rfind(delim, 0, max_chars)
            if pos != -1 and pos > split_at - 200:
                split_at = pos + 1
                break
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()

    return chunks


def _generate_audio_chunk(
    client: ElevenLabs,
    text: str,
    voice_id: str,
) -> bytes:
    """
    Generate audio for a single text chunk.
    Returns raw MP3 bytes.
    """
    voice_settings = VoiceSettings(
        stability=config.ELEVENLABS_STABILITY,
        similarity_boost=config.ELEVENLABS_SIMILARITY_BOOST,
        style=config.ELEVENLABS_STYLE,
        use_speaker_boost=config.ELEVENLABS_USE_SPEAKER_BOOST,
    )

    audio_stream = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=config.ELEVENLABS_MODEL_ID,
        voice_settings=voice_settings,
    )

    # Collect streaming bytes
    audio_bytes = b""
    for chunk in audio_stream:
        if chunk:
            audio_bytes += chunk

    return audio_bytes


def _get_voice_id(client: ElevenLabs, preferred_voice_id: str) -> str:
    """
    Resolve voice ID.
    If preferred_voice_id is set, verify it exists.
    Otherwise, return the first available voice.
    """
    voices_response = client.voices.get_all()
    available = {v.voice_id: v.name for v in voices_response.voices}

    if preferred_voice_id and preferred_voice_id in available:
        return preferred_voice_id

    if preferred_voice_id:
        print(
            f"  ⚠️  Voice ID '{preferred_voice_id}' not found. "
            f"Falling back to first available voice."
        )

    if not available:
        raise RuntimeError("No ElevenLabs voices available on this account.")

    first_id = next(iter(available))
    print(f"  🎙️  Using voice: {available[first_id]} ({first_id})")
    return first_id


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_audio(
    script: VideoScript | None = None,
    voice_id: str = "",
    output_path: Path | None = None,
) -> Path:
    """
    Generate a voiceover MP3 from the script.

    Args:
        script:      VideoScript object. If None, loads from script.json.
        voice_id:    ElevenLabs voice ID. Falls back to config, then first available.
        output_path: Where to save the MP3. Defaults to config.VOICEOVER_PATH.

    Returns:
        Path to the saved voiceover.mp3

    Raises:
        RuntimeError: on API failure or missing voices
        FileNotFoundError: if script.json is missing and no script is provided
    """
    config.validate_config(require_nvidia=False, require_elevenlabs=True)

    if script is None:
        script = load_script()

    if output_path is None:
        output_path = config.VOICEOVER_PATH

    full_text = _build_full_text(script)
    if not full_text.strip():
        raise ValueError("Script has no narration text to convert to audio.")

    client = _get_client()

    # Resolve voice
    resolved_voice_id = _get_voice_id(
        client,
        voice_id or config.ELEVENLABS_VOICE_ID,
    )

    chunks = _chunk_text(full_text)
    all_audio = b""

    for i, chunk in enumerate(chunks, start=1):
        if len(chunks) > 1:
            print(f"  🎙️  Generating audio chunk {i}/{len(chunks)} …")
        retries = 3
        for attempt in range(1, retries + 1):
            try:
                all_audio += _generate_audio_chunk(client, chunk, resolved_voice_id)
                break
            except Exception as e:
                if attempt == retries:
                    raise RuntimeError(
                        f"ElevenLabs API failed after {retries} attempts: {e}"
                    ) from e
                wait = 2 ** attempt
                print(f"    ⏳ Attempt {attempt} failed — retrying in {wait}s …")
                time.sleep(wait)

    # Write MP3 to disk
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(all_audio)

    return output_path
