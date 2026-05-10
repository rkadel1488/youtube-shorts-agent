"""
Generates a YouTube Shorts script + supporting metadata.

Loads a pre-written script from scripts/{niche}/{i:02d}.json (fast, no API call).
Falls back to Claude API generation if no pre-written scripts are available.

Output schema (JSON):
{
  "topic": "...",
  "hook": "...",
  "script": "...",
  "keywords": ["word1", "word2", ...]
}
"""
import json
import random
import time
from pathlib import Path

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, STORY_TOPICS
from utils.logger import get_logger

log = get_logger(__name__)

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"

SYSTEM_PROMPT = """You are an expert YouTube Shorts scriptwriter.
Your scripts go viral because they open with an irresistible hook, use short punchy sentences,
build curiosity, reveal something surprising, and end with a clear call-to-action.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

SCRIPT_TEMPLATE = """Write a YouTube Shorts script for the niche: {niche_label}.

Topic to cover: {topic}

Rules:
- Total spoken length: 20–27 seconds (~60-75 words)
- Hook (first sentence): shock/curiosity-gap based on the topic, under 12 words
- Body: short sentences (max 10 words each), build tension, deliver a surprising fact or reveal
- CTA (last sentence): "Follow for [specific benefit]."

Return ONLY this JSON (no markdown):
{{
  "topic": "{topic}",
  "hook": "the opening hook line only",
  "script": "full script including hook, body, and CTA",
  "keywords": ["3-5 single English words useful for finding relevant images"]
}}"""


def _load_from_disk(niche_name: str) -> dict | None:
    """Pick a random pre-written script JSON from scripts/{niche}/."""
    niche_dir = SCRIPTS_DIR / niche_name
    if not niche_dir.exists():
        return None
    files = sorted(niche_dir.glob("*.json"))
    if not files:
        return None
    chosen = random.choice(files)
    try:
        data = json.loads(chosen.read_text(encoding="utf-8"))
        for key in ("topic", "hook", "script", "keywords"):
            if key not in data:
                raise ValueError(f"Missing key '{key}' in {chosen}")
        log.info("Loaded pre-written script from %s: '%s'", chosen.name, data["topic"])
        return data
    except Exception as exc:
        log.warning("Failed to load %s: %s", chosen, exc)
        return None


def generate_script(niche: dict, retries: int = 3) -> dict:
    """
    Load a pre-written script from disk, or fall back to Claude API.
    Returns a dict with keys: topic, hook, script, keywords.
    """
    result = _load_from_disk(niche["name"])
    if result:
        return result

    log.info("No pre-written scripts found for '%s' — calling Claude API", niche["name"])
    topics = STORY_TOPICS.get(niche["name"], [])
    topic = random.choice(topics) if topics else niche["label"]
    log.info("Selected storyline: '%s'", topic)
    prompt = SCRIPT_TEMPLATE.format(niche_label=niche["label"], topic=topic)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    for attempt in range(1, retries + 1):
        try:
            log.info("Generating script for niche '%s' (attempt %d)…", niche["label"], attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            api_result = json.loads(raw)

            for key in ("topic", "hook", "script", "keywords"):
                if key not in api_result:
                    raise ValueError(f"Missing key '{key}' in Claude response")

            log.info("Script generated via API: '%s'", api_result["topic"])
            return api_result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Script generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Script generation failed after {retries} attempts")
