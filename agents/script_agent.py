"""
Generates a YouTube Shorts script + supporting metadata using Claude.

Claude freely picks any random niche and topic each run — no predefined categories.

Output schema (JSON):
{
  "topic": "...",
  "hook": "...",
  "script": "...",
  "keywords": ["word1", "word2", ...]
}
"""
import json
import time

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from utils.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert YouTube Shorts scriptwriter.
Your scripts go viral because they open with an irresistible hook, use short punchy sentences,
build curiosity, reveal something surprising, and end with a clear call-to-action.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

SCRIPT_TEMPLATE = """Pick ANY random fascinating topic and write a YouTube Shorts script for it.

Choose from any area: history, science, sports, nature, space, psychology, mysteries, \
true crime, world records, animals, technology, ancient civilizations, movies, music, \
famous people, strange laws, unsolved mysteries, or anything else you find compelling.

Rules:
- Total spoken length: 20–27 seconds (~60-75 words)
- Hook (first sentence): shock/curiosity-gap, under 12 words
- Body: short sentences (max 10 words each), build tension, deliver a surprising fact or reveal
- CTA (last sentence): "Follow for [specific benefit]."

Return ONLY this JSON (no markdown):
{
  "topic": "a short descriptive title for this story",
  "hook": "the opening hook line only",
  "script": "full script including hook, body, and CTA",
  "keywords": ["3-5 single English words useful for finding relevant images"]
}"""


def generate_script(retries: int = 3) -> dict:
    """
    Ask Claude to freely pick any topic and write a Shorts script.
    Returns a dict with keys: topic, hook, script, keywords.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating random script (attempt %d)…", attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": SCRIPT_TEMPLATE}],
            )
            raw = message.content[0].text.strip()
            result = json.loads(raw)

            for key in ("topic", "hook", "script", "keywords"):
                if key not in result:
                    raise ValueError(f"Missing key '{key}' in Claude response")

            log.info("Script generated: '%s'", result["topic"])
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Script generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Script generation failed after {retries} attempts")
