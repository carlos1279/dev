"""
video_assembler.py — VideoCreatorAI Video Assembler

Scans ./media/ for sequentially named files, loads each for exactly 5 seconds,
concatenates them, overlays voiceover.mp3, and exports output/output.mp4.

Supports mixed media: static images (ImageClip) and video clips (VideoFileClip).
"""

from __future__ import annotations

import re
from pathlib import Path

from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx import Resize

import config


# ---------------------------------------------------------------------------
# Media discovery
# ---------------------------------------------------------------------------
def _discover_media_files(media_dir: Path) -> list[Path]:
    """
    Scan media_dir for files with sequential numeric names (e.g. 001.jpg).
    Returns sorted list of Paths.
    Supported extensions: image and video as defined in config.
    """
    all_extensions = config.IMAGE_EXTENSIONS | config.VIDEO_EXTENSIONS
    candidates: list[tuple[int, Path]] = []

    for f in media_dir.iterdir():
        if not f.is_file():
            continue
        if f.suffix.lower() not in all_extensions:
            continue
        # Extract leading numeric index from filename
        match = re.match(r"^(\d+)", f.stem)
        if match:
            candidates.append((int(match.group(1)), f))

    if not candidates:
        return []

    candidates.sort(key=lambda x: x[0])
    return [p for _, p in candidates]


# ---------------------------------------------------------------------------
# Clip builders
# ---------------------------------------------------------------------------
def _build_image_clip(path: Path, duration: int) -> ImageClip:
    """Create a resized ImageClip for the given duration."""
    clip = ImageClip(str(path), duration=duration)
    clip = Resize(clip, (config.VIDEO_WIDTH, config.VIDEO_HEIGHT))
    return clip.with_fps(config.VIDEO_FPS)


def _build_video_clip(path: Path, duration: int) -> VideoFileClip:
    """
    Load a VideoFileClip trimmed / looped to exactly `duration` seconds.
    Also resizes to target resolution.
    """
    clip = VideoFileClip(str(path))

    if clip.duration < duration:
        # Loop the clip to fill the required duration
        loops = int(duration / clip.duration) + 1
        clip = concatenate_videoclips([clip] * loops)

    # Trim to exact duration
    clip = clip.subclipped(0, duration)
    clip = Resize(clip, (config.VIDEO_WIDTH, config.VIDEO_HEIGHT))
    return clip.with_fps(config.VIDEO_FPS)


def _build_clip(path: Path, duration: int):
    """Route to image or video builder based on file extension."""
    suffix = path.suffix.lower()
    if suffix in config.IMAGE_EXTENSIONS:
        return _build_image_clip(path, duration)
    elif suffix in config.VIDEO_EXTENSIONS:
        return _build_video_clip(path, duration)
    else:
        raise ValueError(f"Unsupported media file type: {path}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def assemble_video(
    media_dir: Path | None = None,
    audio_path: Path | None = None,
    output_path: Path | None = None,
    segment_duration: int | None = None,
    num_segments: int | None = None,
) -> Path:
    """
    Assemble the final video from media files and voiceover audio.

    Args:
        media_dir:        Directory containing numbered media files.
        audio_path:       Path to voiceover.mp3.
        output_path:      Where to save output.mp4.
        segment_duration: Seconds per segment (default: config.SEGMENT_DURATION).
        num_segments:     Expected number of segments from the script.
                          Used for warning if media count doesn't match.

    Returns:
        Path to the output video.

    Raises:
        FileNotFoundError: if no media files or audio file are found.
        RuntimeError: on assembly failure.
    """
    if media_dir is None:
        media_dir = config.MEDIA_DIR
    if audio_path is None:
        audio_path = config.VOICEOVER_PATH
    if output_path is None:
        output_path = config.OUTPUT_VIDEO_PATH
    if segment_duration is None:
        segment_duration = config.SEGMENT_DURATION

    # ── Validate inputs ──────────────────────────────────────────────────
    if not audio_path.exists():
        raise FileNotFoundError(
            f"Voiceover not found at {audio_path}. "
            "Run the audio generator first."
        )

    media_files = _discover_media_files(media_dir)
    if not media_files:
        raise FileNotFoundError(
            f"No media files found in {media_dir}.\n"
            "Place files named 001.jpg, 002.mp4, 003.jpg … in that folder.\n"
            "Check visual_prompts.txt for the prompts to generate each clip."
        )

    if num_segments and len(media_files) != num_segments:
        print(
            f"  ⚠️  Warning: script has {num_segments} segments but "
            f"{len(media_files)} media files were found. "
            "Some segments may be missing or audio may be out of sync."
        )

    # ── Build individual clips ────────────────────────────────────────────
    clips = []
    print(f"  🎞️  Loading {len(media_files)} media file(s) …")
    for i, path in enumerate(media_files, start=1):
        print(f"    [{i:02d}/{len(media_files):02d}] {path.name}")
        try:
            clip = _build_clip(path, segment_duration)
            clips.append(clip)
        except Exception as e:
            print(f"    ⚠️  Skipping {path.name}: {e}")

    if not clips:
        raise RuntimeError("No clips could be loaded. Check media files.")

    # ── Concatenate clips ─────────────────────────────────────────────────
    print("  🔗  Concatenating clips …")
    final_clip = concatenate_videoclips(clips, method="compose")

    # ── Add audio track ───────────────────────────────────────────────────
    print("  🎵  Adding voiceover audio …")
    audio = AudioFileClip(str(audio_path))

    # Trim audio to video length if longer, or loop if shorter
    video_duration = final_clip.duration
    if audio.duration > video_duration:
        audio = audio.subclipped(0, video_duration)

    final_clip = final_clip.with_audio(audio)

    # ── Export ────────────────────────────────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"  💾  Exporting to {output_path} …")
    final_clip.write_videofile(
        str(output_path),
        fps=config.VIDEO_FPS,
        codec=config.VIDEO_CODEC,
        audio_codec=config.AUDIO_CODEC,
        logger=None,          # Suppress MoviePy's verbose output
        threads=4,
    )

    # Clean up
    for clip in clips:
        clip.close()
    audio.close()
    final_clip.close()

    return output_path
