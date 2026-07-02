"""
transcription.py — VideoCreatorAI Whisper Transcription

Sends voiceover.mp3 to OpenAI Whisper API for word-level transcription,
saves timestamps.json, and generates subtitles.ass with karaoke effect.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openai import OpenAI

import config


# ---------------------------------------------------------------------------
# Whisper API call
# ---------------------------------------------------------------------------
def _transcribe_with_whisper(audio_path: Path) -> dict[str, Any]:
    """
    Transcribe audio using OpenAI Whisper API with word-level timestamps.
    
    Returns:
        Dict with 'words' list and 'duration'
    """
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model=config.WHISPER_MODEL,
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["word"],
        )
    
    # Extract word-level timestamps
    words = [
        {
            "word": word.word,
            "start": word.start,
            "end": word.end,
        }
        for word in response.words
    ]
    
    return {
        "words": words,
        "duration": response.duration,
    }


# ---------------------------------------------------------------------------
# ASS subtitle generation with karaoke effect
# ---------------------------------------------------------------------------
def _generate_ass_subtitle(timestamps: dict[str, Any]) -> str:
    """
    Generate ASS (Advanced SubStation Alpha) subtitle file with karaoke effect.
    
    ASS format supports \k karaoke tags for word-by-word highlighting.
    """
    words = timestamps["words"]
    
    # ASS header
    ass_header = """[Script Info]
Title: VideoCreatorAI Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{primary},{secondary},{outline},&H000000&,1,0,0,0,100,100,0,0,1,{outline_width},2,2,2,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""".format(
        font=config.SUBTITLE_FONT,
        size=config.SUBTITLE_FONT_SIZE,
        primary=config.SUBTITLE_PRIMARY_COLOR,
        secondary=config.SUBTITLE_PRIMARY_COLOR,
        outline=config.SUBTITLE_OUTLINE_COLOR,
        outline_width=config.SUBTITLE_OUTLINE_WIDTH,
        margin_v=config.SUBTITLE_MARGIN_V,
    )
    
    # Group words into lines (approx 3-4 words per line for readability)
    lines = []
    current_line = []
    current_line_words = []
    
    for word_data in words:
        current_line.append(word_data)
        current_line_words.append(word_data["word"])
        
        # Start new line after ~3-4 words
        if len(current_line) >= 3:
            lines.append(current_line)
            current_line = []
    
    if current_line:
        lines.append(current_line)
    
    # Generate dialogue events with karaoke timing
    events = []
    for line in lines:
        if not line:
            continue
        
        start_time = line[0]["start"]
        end_time = line[-1]["end"]
        
        # Convert seconds to ASS time format (H:MM:SS.cc)
        start_ass = _seconds_to_ass_time(start_time)
        end_ass = _seconds_to_ass_time(end_time)
        
        # Build text with karaoke tags
        text_parts = []
        for word_data in line:
            word = word_data["word"]
            duration = word_data["end"] - word_data["start"]
            # \k duration is in centiseconds
            karaoke_duration = int(duration * 100)
            text_parts.append(f"\\{karaoke_duration}k{word}")
        
        text = "".join(text_parts)
        
        events.append(
            f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{text}"
        )
    
    return ass_header + "\n".join(events)


def _seconds_to_ass_time(seconds: float) -> str:
    """Convert seconds to ASS time format (H:MM:SS.cc)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def transcribe_audio(audio_path: Path | None = None) -> Path:
    """
    Transcribe voiceover audio using Whisper and generate ASS subtitles.
    
    Args:
        audio_path: Path to voiceover.mp3. Defaults to config.VOICEOVER_PATH.
    
    Returns:
        Path to the generated subtitles.ass file.
    
    Raises:
        RuntimeError: on API failure
        FileNotFoundError: if audio file doesn't exist
    """
    config.validate_config(require_openai=True)
    
    if audio_path is None:
        audio_path = config.VOICEOVER_PATH
    
    if not audio_path.exists():
        raise FileNotFoundError(
            f"Audio file not found at {audio_path}. "
            "Run the audio generator first."
        )
    
    print(f"  🎙️  Transcribing {audio_path.name} with Whisper …")
    timestamps = _transcribe_with_whisper(audio_path)
    
    # Save timestamps.json
    with open(config.TIMESTAMPS_PATH, "w", encoding="utf-8") as f:
        json.dump(timestamps, f, indent=2, ensure_ascii=False)
    print(f"  ✅  Timestamps saved: {config.TIMESTAMPS_PATH}")
    
    # Generate and save subtitles.ass
    ass_content = _generate_ass_subtitle(timestamps)
    with open(config.SUBTITLES_PATH, "w", encoding="utf-8") as f:
        f.write(ass_content)
    print(f"  ✅  Subtitles saved: {config.SUBTITLES_PATH}")
    
    return config.SUBTITLES_PATH
