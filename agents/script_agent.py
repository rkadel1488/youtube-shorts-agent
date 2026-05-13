"""
Generates a YouTube Shorts script + supporting metadata using Claude.

A random category is injected into the prompt each run so Claude is pushed
into a different area every time — guaranteed topic variety across all posts.

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

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from utils.logger import get_logger

log = get_logger(__name__)

# Large pool of categories — one is picked at random each run to force variety
RANDOM_CATEGORIES = [
    "ancient history", "space exploration", "unsolved mysteries", "world records",
    "animal behavior", "human psychology", "true crime", "famous inventions",
    "natural disasters", "bizarre laws", "medical breakthroughs", "lost civilizations",
    "sports legends", "ocean discoveries", "military history", "famous heists",
    "extinct creatures", "conspiracy theories proven true", "child prodigies",
    "volcanic eruptions", "survival stories", "famous disappearances", "royal scandals",
    "accidental discoveries", "haunted places", "world war secrets", "extreme weather",
    "record-breaking feats", "forgotten empires", "time capsule discoveries",
    "bizarre coincidences", "famous last words", "underground cities", "mind-bending math",
    "human body facts", "deepest ocean secrets", "cold war secrets", "prison escapes",
    "famous forgeries", "extinct languages", "rogue scientists", "curse legends",
    "abandoned places", "secret societies", "ancient engineering", "famous rivalries",
    "volcanic islands", "quirky world records", "famous poisonings", "buried treasures",
    "historical hoaxes", "jungle discoveries", "aviation mysteries", "ship wrecks",
    "famous prophecies", "desert survival", "Arctic exploration", "criminal masterminds",
    "brain science", "optical illusions explained", "rare genetic conditions",
    "fastest humans ever", "oldest living things", "deadliest animals", "deepest caves",
    "tallest structures in history", "richest people ever", "strangest festivals",
    "famous feuds", "war propaganda", "forgotten heroes", "child rulers in history",
    "longest wars", "smallest countries", "greatest escapes", "impossible architecture",
]

SYSTEM_PROMPT = """You are an expert YouTube Shorts scriptwriter.
Your scripts go viral because they open with an irresistible hook, use short punchy sentences,
build curiosity, reveal something surprising, and end with a clear call-to-action.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

SCRIPT_TEMPLATE = """Write a YouTube Shorts script about a specific fascinating story within the category: {category}

Pick ONE specific story, event, person, or fact from that category that most people don't know about.

Rules:
- Total spoken length: 20–27 seconds (~60-75 words)
- Hook (first sentence): shock/curiosity-gap, under 12 words
- Body: short sentences (max 10 words each), build tension, deliver a surprising fact or reveal
- CTA (last sentence): "Follow for [specific benefit]."

Return ONLY this JSON (no markdown):
{{
  "topic": "a short descriptive title for this specific story",
  "hook": "the opening hook line only",
  "script": "full script including hook, body, and CTA",
  "keywords": ["3-5 single English words useful for finding relevant images"]
}}"""


def generate_script(retries: int = 3) -> dict:
    """
    Pick a random category, then ask Claude to write a Shorts script for a story within it.
    Returns a dict with keys: topic, hook, script, keywords.
    """
    category = random.choice(RANDOM_CATEGORIES)
    log.info("Random category selected: '%s'", category)
    prompt = SCRIPT_TEMPLATE.format(category=category)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating script (attempt %d)…", attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
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
