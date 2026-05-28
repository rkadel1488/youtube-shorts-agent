"""
Generates a YouTube Shorts cricket highlight script using Claude.

Fetches real recent match data first, then asks Claude to write
an exciting highlight commentary script based on that data.

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

from agents.cricket_agent import get_recent_matches
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from utils.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You are an electrifying cricket highlights commentator for YouTube Shorts.
Your scripts sound like the most exciting moment of a match — urgent, vivid, fast-paced.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

SCRIPT_TEMPLATE = """Write a YouTube Shorts cricket highlight script based on this recent match data:

{match_info}

Rules:
- Total spoken length: 20-27 seconds (~60-75 words)
- Hook (first line, under 12 words): must grab attention instantly. Use one of:
    • "This moment will be talked about for years."
    • "[Player/Team] just did the impossible."
    • "Nobody saw this coming in [match name]."
    • "[Score/stat] — cricket has never seen anything like it."
- Body: short punchy sentences (max 10 words). Build the tension, describe the key moment, deliver the result.
- End with: "Follow for daily cricket highlights."
- Write like a live commentator — use present tense, energy, drama.

Return ONLY this JSON (no markdown):
{{
  "topic": "short punchy title for this highlight (e.g. 'India vs Australia — Final Over Thriller')",
  "hook": "the opening hook line only",
  "script": "full script including hook, body, and CTA",
  "keywords": ["cricket", "stadium", "batting", "bowling", "cricket match"]
}}"""

FALLBACK_TEMPLATE = """Write a YouTube Shorts script about one of the most dramatic moments \
in recent international cricket — a match-winning six, a stunning wicket, or a record-breaking innings.

Rules:
- Total spoken length: 20-27 seconds (~60-75 words)
- Hook (first line, under 12 words): instant attention-grabber about a cricket moment
- Body: short punchy sentences (max 10 words each), build tension, deliver the highlight
- End with: "Follow for daily cricket highlights."
- Write with the energy of a live commentator.

Return ONLY this JSON (no markdown):
{{
  "topic": "short punchy title for this highlight",
  "hook": "the opening hook line only",
  "script": "full script including hook, body, and CTA",
  "keywords": ["cricket", "stadium", "batting", "bowling", "cricket match"]
}}"""


def generate_script(retries: int = 3) -> dict:
    """
    Fetch recent cricket match data and generate a highlight script via Claude.
    Falls back to generic cricket highlight if no live data is available.
    """
    matches = get_recent_matches()

    if matches:
        match = random.choice(matches)
        parts = [f"Match: {match['name']}"]
        if match.get("score1"):
            parts.append(f"{match['team1']}: {match['score1']}")
        if match.get("score2"):
            parts.append(f"{match['team2']}: {match['score2']}")
        if match.get("status"):
            parts.append(f"Status: {match['status']}")
        if match.get("note"):
            parts.append(f"Note: {match['note']}")
        match_info = "\n".join(parts)
        prompt = SCRIPT_TEMPLATE.format(match_info=match_info)
        log.info("Generating highlight script for: %s", match["name"])
    else:
        prompt = FALLBACK_TEMPLATE
        log.info("No live data — generating generic cricket highlight script")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    for attempt in range(1, retries + 1):
        try:
            log.info("Calling Claude for script (attempt %d)...", attempt)
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
