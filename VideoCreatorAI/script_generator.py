"""
script_generator.py — VideoCreatorAI Script Generator

Sends the product name/URL to OpenRouter/Llama and receives a structured
JSON script composed of 5-second segments, each with:
  - 'text'          : narration the voiceover will speak
  - 'visual_prompt' : cinematic AI prompt for Runway / Kling / Flux

Also extracts a 'thumbnail_question' for the video thumbnail.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import requests
from pydantic import BaseModel, ValidationError

import config


# ---------------------------------------------------------------------------
# Pydantic schema for a single 5-second script segment
# ---------------------------------------------------------------------------
class ScriptSegment(BaseModel):
    text: str
    visual_prompt: str
    search_keywords: list[str] = []  # 2-4 keywords for asset hunting (Pexels/Pixabay)


class VideoScript(BaseModel):
    thumbnail_question: str
    segments: list[ScriptSegment]


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
You are an expert video scriptwriter and AI prompt engineer specialising in \
high-retention affiliate marketing videos for the USA/Global market.

When given a product name or URL, you MUST return a single valid JSON object \
(no markdown fences, no extra text) with this exact structure:

{
  "thumbnail_question": "<A short, shocking question for the thumbnail (max 10 words)>",
  "segments": [
    {
      "text": "<Exact words the narrator speaks for this 5-second block>",
      "visual_prompt": "<Detailed cinematic prompt for stock footage (Pexels/Pixabay) or AI generation>",
      "search_keywords": ["keyword1", "keyword2", "keyword3"]
    }
  ]
}

Video structure rules:
1. HOOK (first segment, 0-5 s): Immediately and shockingly answers the thumbnail question.
2. BODY (next 3-4 segments): Introduce common user problems one by one and show the product as the solution.
3. Each 'text' should be concise enough to be spoken naturally in 5 seconds (≈ 15-20 words).
4. Each 'visual_prompt' must be hyper-detailed and cinematic, optimized for stock footage:
   "Cinematic 4K hyper-realistic [subject], [action], [lighting style], [camera angle], \
[mood], studio quality, no text"
5. Each 'search_keywords' should contain 2-4 specific keywords for stock video search \
(e.g., ["stoic man", "dark forest", "abstract 3d", "cinematic b-roll"])
6. Produce exactly 5-8 segments total.
7. Return ONLY the JSON object — no explanations, no markdown.

Tone: Dark psychology, stoicism, personal growth, hypnotic narration.
Language: English ONLY (for USA/Global market, high CPM).
"""

_USER_PROMPT_TEMPLATE = """\
Create a high-retention affiliate marketing video script for the following product:

{product}

Remember: return ONLY the JSON object as specified.
"""


# ---------------------------------------------------------------------------
# OpenRouter / Llama API call with retries
# ---------------------------------------------------------------------------
def _call_llm_provider(product: str) -> str:
    """Call the OpenRouter Llama endpoint and return the raw text response."""
    headers = {
        "Authorization": f"Bearer {config.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _USER_PROMPT_TEMPLATE.format(product=product)},
        ],
        "max_tokens": min(config.LLM_MAX_TOKENS, 8192),
        "temperature": config.LLM_TEMPERATURE,
    }

    last_error: Exception | None = None
    for attempt in range(1, config.LLM_MAX_RETRIES + 1):
        try:
            response = requests.post(
                f"{config.LLM_API_BASE.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=config.LLM_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

        except requests.exceptions.Timeout as e:
            last_error = e
            wait = 2 ** attempt
            print(f"  ⏳ Attempt {attempt} timed out — retrying in {wait}s …")
            time.sleep(wait)

        except requests.exceptions.HTTPError as e:
            raise RuntimeError(
                f"OpenRouter Llama API error {response.status_code}: {response.text}"
            ) from e

        except requests.exceptions.RequestException as e:
            last_error = e
            wait = 2 ** attempt
            print(f"  ⚠️  Attempt {attempt} failed ({e}) — retrying in {wait}s …")
            time.sleep(wait)

    raise RuntimeError(
        f"OpenRouter Llama API failed after {config.LLM_MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


def _call_nvidia_nim(product: str) -> str:
    """Backward-compatible wrapper for the former NVIDIA entry point."""
    return _call_llm_provider(product)


# ---------------------------------------------------------------------------
# JSON extraction and validation
# ---------------------------------------------------------------------------
def _extract_json(raw: str) -> dict[str, Any]:
    """
    Extract and parse JSON from the model response.
    Handles cases where the model wraps the JSON in markdown code fences.
    """
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()

    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find the first {...} block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not parse JSON from model response.\n"
        f"Raw response:\n{raw[:500]}"
    )


def _validate_script(data: dict[str, Any]) -> VideoScript:
    """Validate parsed JSON against the VideoScript Pydantic model."""
    try:
        return VideoScript(**data)
    except ValidationError as e:
        raise ValueError(f"Script JSON schema invalid:\n{e}") from e


# ---------------------------------------------------------------------------
# Save outputs
# ---------------------------------------------------------------------------
def _save_outputs(script: VideoScript) -> None:
    """Persist script.json and visual_prompts.txt to disk."""
    # Save full script JSON
    with open(config.SCRIPT_PATH, "w", encoding="utf-8") as f:
        json.dump(script.model_dump(), f, indent=2, ensure_ascii=False)

    # Save human-readable visual prompts file
    lines: list[str] = [
        "=" * 70,
        "VideoCreatorAI — Visual Prompts",
        "=" * 70,
        f"Thumbnail question: {script.thumbnail_question}",
        "",
    ]
    for i, seg in enumerate(script.segments, start=1):
        lines.append(f"Segment {i:02d}  [{(i - 1) * 5}s – {i * 5}s]")
        lines.append(f"  Narration : {seg.text}")
        lines.append(f"  Visual    : {seg.visual_prompt}")
        lines.append("")

    with open(config.VISUAL_PROMPTS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_script(product: str) -> VideoScript:
    """
    Generate a VideoScript for the given product name or URL.

    Steps:
      1. Call NVIDIA NIM API
      2. Parse and validate the JSON response
      3. Save script.json and visual_prompts.txt
      4. Return the VideoScript object

    Raises:
      RuntimeError: on API failure
      ValueError: on invalid JSON / schema mismatch
    """
    config.validate_config(require_elevenlabs=False)

    raw_response = _call_llm_provider(product)
    data = _extract_json(raw_response)
    script = _validate_script(data)
    _save_outputs(script)

    return script


def load_script() -> VideoScript:
    """
    Load an existing script.json from disk.
    Used when skipping the generation step.
    """
    if not config.SCRIPT_PATH.exists():
        raise FileNotFoundError(
            f"script.json not found at {config.SCRIPT_PATH}. "
            "Run the script generator first."
        )
    with open(config.SCRIPT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _validate_script(data)
