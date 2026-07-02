"""
ffmpeg_assembler.py — VideoCreatorAI FFmpeg Assembler

Assembles the final video using FFmpeg with Ken Burns effect and ASS subtitles.
Replaces MoviePy for the automated pipeline (MoviePy remains as fallback).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import config

try:
    from imageio_ffmpeg import get_ffmpeg_exe
    FFMPEG_PATH = get_ffmpeg_exe()
except ImportError:
    FFMPEG_PATH = "ffmpeg"


# ---------------------------------------------------------------------------
# FFmpeg filter graph builders
# ---------------------------------------------------------------------------
def _build_ken_burns_filter() -> str:
    """Build the Ken Burns zoompan filter string."""
    zoom_factor = config.KEN_BURNS_ZOOM_FACTOR
    pan_speed = config.KEN_BURNS_PAN_SPEED
    
    # zoompan filter: gradual zoom from 1.0 to zoom_factor with subtle pan
    filter_str = (
        f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        f"zoompan=z='min(zoom+{pan_speed},{zoom_factor})':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=150:s=1920x1080:fps=30"
    )
    return filter_str


def _process_clip(input_path: Path, output_path: Path, duration: int = 5) -> bool:
    """
    Process a single video clip with Ken Burns effect and trim to duration.
    
    Args:
        input_path: Path to source video
        output_path: Path to save processed clip
        duration: Target duration in seconds
    
    Returns:
        True if successful, False otherwise
    """
    ken_burns_filter = _build_ken_burns_filter()
    
    cmd = [
        FFMPEG_PATH,
        "-i", str(input_path),
        "-vf", ken_burns_filter,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-y",  # Overwrite output
        str(output_path),
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"    ⚠️  FFmpeg error: {result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"    ⚠️  FFmpeg timeout processing {input_path.name}")
        return False
    except Exception as e:
        print(f"    ⚠️  FFmpeg error: {e}")
        return False


def _create_concat_file(media_files: list[Path], concat_file: Path) -> None:
    """Create FFmpeg concat demuxer file."""
    with open(concat_file, "w", encoding="utf-8") as f:
        for media_path in media_files:
            f.write(f"file '{media_path.absolute()}'\n")


def _assemble_with_subtitles(
    concat_file: Path,
    audio_path: Path,
    ass_path: Path,
    output_path: Path,
) -> bool:
    """
    Concatenate clips, burn in subtitles, and mux audio.
    
    Args:
        concat_file: Path to concat demuxer file
        audio_path: Path to voiceover audio
        ass_path: Path to ASS subtitle file
        output_path: Path to final output video
    
    Returns:
        True if successful, False otherwise
    """
    # FFmpeg filter complex for subtitles
    # Note: ASS subtitles require the subtitles filter with force_style
    subtitle_filter = f"subtitles={ass_path.absolute()}:force_style='Fontsize={config.SUBTITLE_FONT_SIZE},PrimaryColour={config.SUBTITLE_PRIMARY_COLOR},OutlineColour={config.SUBTITLE_OUTLINE_COLOR},Outline={config.SUBTITLE_OUTLINE_WIDTH}'"
    
    cmd = [
        FFMPEG_PATH,
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-i", str(audio_path),
        "-vf", subtitle_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",  # Trim to shortest stream
        "-y",  # Overwrite output
        str(output_path),
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            print(f"    ⚠️  FFmpeg assembly error: {result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"    ⚠️  FFmpeg assembly timeout")
        return False
    except Exception as e:
        print(f"    ⚠️  FFmpeg assembly error: {e}")
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def assemble_with_ffmpeg(
    media_files: list[Path],
    audio_path: Path | None = None,
    ass_path: Path | None = None,
    output_path: Path | None = None,
    segment_duration: int = 5,
) -> Path:
    """
    Assemble the final video using FFmpeg with Ken Burns effect and subtitles.
    
    Args:
        media_files: List of Paths to media files (ordered by segment)
        audio_path: Path to voiceover audio. Defaults to config.VOICEOVER_PATH.
        ass_path: Path to ASS subtitle file. Defaults to config.SUBTITLES_PATH.
        output_path: Path to save output video. Defaults to config.OUTPUT_VIDEO_PATH.
        segment_duration: Duration per segment in seconds. Defaults to 5.
    
    Returns:
        Path to the assembled video.
    
    Raises:
        FileNotFoundError: if media files or audio are missing
        RuntimeError: if assembly fails
    """
    if audio_path is None:
        audio_path = config.VOICEOVER_PATH
    if ass_path is None:
        ass_path = config.SUBTITLES_PATH
    if output_path is None:
        output_path = config.OUTPUT_VIDEO_PATH
    
    # Validate inputs
    if not media_files:
        raise FileNotFoundError("No media files provided")
    
    if not audio_path.exists():
        raise FileNotFoundError(
            f"Audio file not found at {audio_path}. "
            "Run the audio generator first."
        )
    
    if not ass_path.exists():
        raise FileNotFoundError(
            f"Subtitle file not found at {ass_path}. "
            "Run the transcription module first."
        )
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create temporary directory for processed clips
    temp_dir = config.MEDIA_DIR / "temp_ffmpeg"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each clip with Ken Burns effect
    print(f"  🎞️  Processing {len(media_files)} clips with Ken Burns effect …")
    processed_clips = []
    
    for i, media_file in enumerate(media_files, start=1):
        if not media_file.exists():
            print(f"    ⚠️  Skipping missing file: {media_file.name}")
            continue
        
        output_clip = temp_dir / f"clip_{i:03d}.mp4"
        print(f"    [{i:02d}/{len(media_files):02d}] {media_file.name}")
        
        if _process_clip(media_file, output_clip, segment_duration):
            processed_clips.append(output_clip)
        else:
            print(f"    ⚠️  Failed to process {media_file.name}")
    
    if not processed_clips:
        raise RuntimeError("No clips were successfully processed")
    
    # Create concat demuxer file
    concat_file = temp_dir / "concat.txt"
    _create_concat_file(processed_clips, concat_file)
    
    # Assemble with subtitles and audio
    print("  🔗  Concatenating clips with subtitles and audio …")
    if not _assemble_with_subtitles(concat_file, audio_path, ass_path, output_path):
        raise RuntimeError("FFmpeg assembly failed")
    
    print(f"  ✅  Video assembled: {output_path}")
    
    # Cleanup temp files (optional - comment out to keep for debugging)
    # import shutil
    # shutil.rmtree(temp_dir, ignore_errors=True)
    
    return output_path
