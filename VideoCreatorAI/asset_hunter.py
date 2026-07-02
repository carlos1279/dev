"""
asset_hunter.py — VideoCreatorAI Asset Hunter

Automatically downloads stock footage from Pexels/Pixabay based on script keywords.
Each 5-second segment gets a matching video file (media/001.mp4, 002.mp4, ...).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import requests

import config
from script_generator import VideoScript, load_script


# ---------------------------------------------------------------------------
# Pexels API
# ---------------------------------------------------------------------------
def _search_pexels(query: str, per_page: int = 15) -> list[dict[str, Any]]:
    """Search Pexels for videos matching the query."""
    if not config.PEXELS_API_KEY:
        return []
    
    headers = {"Authorization": config.PEXELS_API_KEY}
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "landscape",
    }
    
    try:
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("videos", [])
    except Exception as e:
        print(f"    ⚠️  Pexels search failed: {e}")
        return []


def _get_best_pexels_video(videos: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Select the best video from Pexels results."""
    if not videos:
        return None
    
    # Filter for videos > 5 seconds (will be trimmed by FFmpeg)
    candidates = [v for v in videos if v.get("duration", 0) >= 5]
    if not candidates:
        candidates = videos  # Fallback to any video
    
    # Prefer HD quality
    candidates = sorted(
        candidates,
        key=lambda v: (
            v.get("width", 0) * v.get("height", 0),
            v.get("duration", 0),
        ),
        reverse=True,
    )
    
    return candidates[0]


def _download_pexels_video(video_data: dict[str, Any], output_path: Path) -> bool:
    """Download a video from Pexels and save to output_path."""
    video_files = video_data.get("video_files", [])
    if not video_files:
        return False
    
    # Select best quality file (prefer HD, landscape)
    video_files = sorted(
        video_files,
        key=lambda f: (f.get("width", 0) * f.get("height", 0)),
        reverse=True,
    )
    best_file = video_files[0]
    download_url = best_file.get("link")
    
    if not download_url:
        return False
    
    try:
        response = requests.get(download_url, timeout=60, stream=True)
        response.raise_for_status()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception as e:
        print(f"    ⚠️  Download failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Pixabay API (fallback)
# ---------------------------------------------------------------------------
def _search_pixabay(query: str, per_page: int = 15) -> list[dict[str, Any]]:
    """Search Pixabay for videos matching the query."""
    if not config.PIXABAY_API_KEY:
        return []
    
    params = {
        "key": config.PIXABAY_API_KEY,
        "q": query,
        "video_type": "film",
        "per_page": per_page,
        "safesearch": "true",
    }
    
    try:
        response = requests.get(
            "https://pixabay.com/api/videos/",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("hits", [])
    except Exception as e:
        print(f"    ⚠️  Pixabay search failed: {e}")
        return []


def _get_best_pixabay_video(videos: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Select the best video from Pixabay results."""
    if not videos:
        return None
    
    # Filter for videos > 5 seconds
    candidates = [v for v in videos if v.get("duration", 0) >= 5]
    if not candidates:
        candidates = videos
    
    # Prefer HD quality
    candidates = sorted(
        candidates,
        key=lambda v: (
            v.get("videos", {}).get("large", {}).get("width", 0) *
            v.get("videos", {}).get("large", {}).get("height", 0),
            v.get("duration", 0),
        ),
        reverse=True,
    )
    
    return candidates[0]


def _download_pixabay_video(video_data: dict[str, Any], output_path: Path) -> bool:
    """Download a video from Pixabay and save to output_path."""
    videos = video_data.get("videos", {})
    if not videos:
        return False
    
    # Prefer large quality, fallback to medium
    for quality in ["large", "medium", "small"]:
        if quality in videos:
            download_url = videos[quality].get("url")
            if download_url:
                try:
                    response = requests.get(download_url, timeout=60, stream=True)
                    response.raise_for_status()
                    
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    return True
                except Exception as e:
                    print(f"    ⚠️  Download failed: {e}")
                    continue
    
    return False


# ---------------------------------------------------------------------------
# Keyword extraction fallback
# ---------------------------------------------------------------------------
def _extract_keywords_from_prompt(visual_prompt: str) -> list[str]:
    """
    Extract search keywords from visual_prompt using regex/heuristics.
    Used as fallback when search_keywords field is empty.
    """
    # Remove common AI prompt prefixes
    prompt = re.sub(
        r"^(Cinematic|4K|hyper-realistic|studio quality|no text)\s*",
        "",
        visual_prompt,
        flags=re.IGNORECASE,
    )
    
    # Extract key phrases (2-3 word sequences)
    words = prompt.split()
    keywords = []
    
    for i in range(len(words) - 1):
        # Skip common filler words
        if words[i].lower() in ["a", "an", "the", "with", "and", "or", "in", "on", "at"]:
            continue
        
        # Create 2-word phrases
        if i + 1 < len(words):
            phrase = f"{words[i]} {words[i+1]}"
            if len(phrase) > 3:
                keywords.append(phrase)
    
    # Also add single important words (nouns/adjectives)
    for word in words:
        if len(word) > 4 and word.lower() not in [
            "with", "from", "style", "light", "dark", "blue", "red",
        ]:
            keywords.append(word)
    
    # Return top 3-4 unique keywords
    unique_keywords = list(dict.fromkeys(keywords))  # Preserve order, remove duplicates
    return unique_keywords[:4]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def fetch_assets(
    script: VideoScript | None = None,
    output_dir: Path | None = None,
) -> list[Path]:
    """
    Download stock footage for each script segment.
    
    Args:
        script: VideoScript object. If None, loads from script.json.
        output_dir: Directory to save media files. Defaults to config.MEDIA_DIR.
    
    Returns:
        List of Paths to downloaded media files.
    
    Raises:
        FileNotFoundError: if script.json is missing
        RuntimeError: if all download attempts fail
    """
    config.validate_config(require_pexels=True)
    
    if script is None:
        script = load_script()
    
    if output_dir is None:
        output_dir = config.MEDIA_DIR
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded_files: list[Path] = []
    used_video_ids: set[str] = set()
    
    print(f"  🎬  Fetching assets for {len(script.segments)} segments …")
    
    for i, segment in enumerate(script.segments, start=1):
        output_path = output_dir / f"{i:03d}.mp4"
        
        # Get search keywords (use field, or extract from visual_prompt)
        keywords = segment.search_keywords
        if not keywords:
            keywords = _extract_keywords_from_prompt(segment.visual_prompt)
        
        if not keywords:
            print(f"    [{i:02d}] ⚠️  No keywords found, skipping")
            continue
        
        print(f"    [{i:02d}] Keywords: {', '.join(keywords)}")
        
        downloaded = False
        
        # Try each keyword with Pexels
        for keyword in keywords:
            if downloaded:
                break
            
            pexels_videos = _search_pexels(keyword)
            if pexels_videos:
                best_video = _get_best_pexels_video(pexels_videos)
                if best_video:
                    video_id = str(best_video.get("id", ""))
                    if video_id not in used_video_ids:
                        print(f"      → Pexels: {best_video.get('url', 'N/A')}")
                        if _download_pexels_video(best_video, output_path):
                            downloaded_files.append(output_path)
                            used_video_ids.add(video_id)
                            downloaded = True
                            break
        
        # Fallback to Pixabay if Pexels failed
        if not downloaded:
            for keyword in keywords:
                if downloaded:
                    break
                
                pixabay_videos = _search_pixabay(keyword)
                if pixabay_videos:
                    best_video = _get_best_pixabay_video(pixabay_videos)
                    if best_video:
                        video_id = str(best_video.get("id", ""))
                        if video_id not in used_video_ids:
                            print(f"      → Pixabay: {best_video.get('pageURL', 'N/A')}")
                            if _download_pixabay_video(best_video, output_path):
                                downloaded_files.append(output_path)
                                used_video_ids.add(video_id)
                                downloaded = True
                                break
        
        if downloaded:
            print(f"    ✅  Saved: {output_path.name}")
        else:
            print(f"    ⚠️  No video found for segment {i}")
    
    print(f"  📦  Downloaded {len(downloaded_files)} media file(s)")
    return downloaded_files
