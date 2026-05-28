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


NICHE_PROMPTS = {
    "fun_facts": """\
Write a mind-blowing fun fact Short script.

Rules:
- Total spoken length: 20-27 seconds (~60-75 words)
- Hook (first line, under 12 words): must make the viewer say "No way!"
- Body: explains the fact in simple vivid terms, short punchy sentences (max 10 words each)
- End with: "Follow for daily mind-blowing facts."

Return ONLY this JSON (no markdown):
{{
  "topic": "short punchy title",
  "hook": "opening hook line",
  "script": "full script including hook, body, and CTA",
  "keywords": ["facts", "mindblow", "didyouknow", "science", "amazing"]
}}""",

    "horror_story": """\
Write a short horror story Short script.

Rules:
- Total spoken length: 20-27 seconds (~60-75 words)
- Hook (first line, under 12 words): must be a spine-chilling opening
- Body: build dread fast with short punchy sentences (max 10 words each)
- End with a twist or scare, then: "Follow for more horror stories."

Return ONLY this JSON (no markdown):
{{
  "topic": "short punchy title",
  "hook": "opening hook line",
  "script": "full script including hook, body, and CTA",
  "keywords": ["horror", "scary", "creepy", "thriller", "horrortok"]
}}""",

    "football": """\
Write a football (soccer) highlights Short script.

Rules:
- Total spoken length: 20-27 seconds (~60-75 words)
- Hook (first line, under 12 words): about a dramatic goal, save, or moment
- Body: build the tension in short punchy sentences (max 10 words each), deliver the result
- End with: "Follow for daily football highlights."
- Write like a live commentator — use present tense, energy, drama.

Return ONLY this JSON (no markdown):
{{
  "topic": "short punchy title",
  "hook": "opening hook line",
  "script": "full script including hook, body, and CTA",
  "keywords": ["football", "soccer", "goals", "highlights", "footballshorts"]
}}""",
}

NICHE_SYSTEM_PROMPT = """You are an electrifying short-form video scriptwriter for YouTube Shorts.
Your scripts are urgent, vivid, fast-paced, and perfectly timed for 20-27 seconds.
Always respond with valid JSON only — no markdown fences, no extra commentary."""


def generate_niche_script(niche: str, retries: int = 3) -> dict:
    """
    Generate a 20-27 second (~60-75 word) YouTube Shorts script for the given niche.
    Supported niches: 'fun_facts', 'horror_story', 'football'.
    Returns a dict with keys: topic, hook, script, keywords.
    """
    if niche not in NICHE_PROMPTS:
        raise ValueError(f"Unknown niche '{niche}'. Supported: {list(NICHE_PROMPTS)}")

    prompt = NICHE_PROMPTS[niche]
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating %s script via Claude (attempt %d)...", niche, attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=512,
                system=NICHE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            result = json.loads(raw)

            for key in ("topic", "hook", "script", "keywords"):
                if key not in result:
                    raise ValueError(f"Missing key '{key}' in Claude response")

            log.info("Niche script generated [%s]: '%s'", niche, result["topic"])
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Niche script generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Niche script generation failed after {retries} attempts")


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
