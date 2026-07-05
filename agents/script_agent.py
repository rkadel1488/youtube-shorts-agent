"""
Generates a YouTube Shorts script for a fixed story topic using Claude.

Each call takes one entry from story_topics.STORY_TOPICS (title + premise +
category) and asks Claude to turn it into a fast-paced hook/build/twist
script under 60 seconds.

Output schema (JSON):
{
  "topic": "...",
  "hook": "...",
  "on_screen_hook": "...",   # short caps version for on-screen display
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

STORY_SYSTEM_PROMPT = """You are a viral short-form video writer for YouTube Shorts with 1M+ view videos.
Your scripts are under 60 seconds, open with a hook that stops the scroll, build tension fast,
and land a twist or payoff at the end. They work for silent viewers since the hook doubles as on-screen text.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

STORY_TEMPLATE = """Write a viral YouTube Shorts story script based on this concept:

Category: {category}
Title: {title}
Premise: {premise}

CRITICAL RULES:
- Total spoken length: 30-50 seconds (~80-130 words)
- Structure: HOOK (the premise itself, max 8 words, second-person "you") → BUILD (3-5 punchy
  present-tense sentences raising tension) → TWIST/PAYOFF (the final 1-2 sentences land the scare,
  laugh, or emotional gut-punch)
- The "on_screen_hook" field is the EXACT text displayed as a large caption — max 6 words, ALL CAPS
- Do not end with a generic CTA like "follow for more" unless it fits the twist naturally

Return ONLY this JSON (no markdown):
{{
  "topic": "{title}",
  "hook": "the opening hook line (max 8 words)",
  "on_screen_hook": "VERY SHORT ON-SCREEN TEXT (max 6 words, ALL CAPS)",
  "script": "full script including hook, build, and twist",
  "keywords": ["3 to 5 visual keywords for AI image generation"]
}}"""


def _avoid_block(used_titles: list = None) -> str:
    """Build a prompt suffix telling Claude which titles to avoid closely paraphrasing."""
    if not used_titles:
        return ""
    recent = used_titles[-20:]
    return ("\n\nALREADY USED TITLES (do NOT repeat or closely paraphrase any of these):\n" +
            "\n".join(f"  - {t}" for t in recent))


def generate_story_script(topic: dict, retries: int = 3, used_titles: list = None) -> dict:
    """
    Generate a 30-50 second YouTube Shorts script for a fixed story topic.
    `topic` is one entry from story_topics.STORY_TOPICS (id, category, title, premise).
    Returns a dict with keys: topic, hook, on_screen_hook, script, keywords.
    """
    prompt = STORY_TEMPLATE.format(
        category=topic["category"], title=topic["title"], premise=topic["premise"],
    ) + _avoid_block(used_titles)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating story script for '%s' via Claude (attempt %d)...",
                     topic["title"], attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=768,
                system=STORY_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            result = json.loads(raw)

            for key in ("topic", "hook", "script", "keywords"):
                if key not in result:
                    raise ValueError(f"Missing key '{key}' in Claude response")

            result.setdefault("on_screen_hook", result["hook"][:40].upper())
            log.info("Story script generated [#%d %s]: '%s'",
                     topic["id"], topic["category"], result["topic"])
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Story script generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Story script generation failed after {retries} attempts")


# ── trend mode (factual explainer, not fiction) ───────────────────────────────

TREND_SYSTEM_PROMPT = """You are a viral short-form video writer for factual, news-style YouTube Shorts.
Your scripts are under 60 seconds, open with a scroll-stopping hook, and deliver real information fast.
You NEVER invent facts — you only use information stated in the premise you are given.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

TREND_TEMPLATE = """Write a factual YouTube Shorts script about this trending topic:

Topic: {title}
What actually happened (your ONLY source of facts): {premise}
Suggested opening angle: {hook_angle}

CRITICAL RULES:
- Total spoken length: 35-50 seconds (~90-130 words)
- Structure: HOOK (max 8 words, surprising) → 4-6 punchy sentences explaining what happened
  and why it matters → CLOSER (a payoff thought or open question, then "Follow for more.")
- Use ONLY facts contained in the premise above. If the premise lacks a detail, do not invent it —
  speak in general terms instead. No made-up numbers, quotes, or names.
- Present tense, conversational, 8th-grade reading level, no emojis, no stage directions
- The "on_screen_hook" field is the EXACT text displayed as a large caption — max 6 words, ALL CAPS

Return ONLY this JSON (no markdown):
{{
  "topic": "{title}",
  "hook": "the opening hook line (max 8 words)",
  "on_screen_hook": "VERY SHORT ON-SCREEN TEXT (max 6 words, ALL CAPS)",
  "script": "full script including hook, explanation, and closer",
  "keywords": ["3 to 5 visual keywords for AI image generation (generic scenes, no real people)"]
}}"""


def generate_trend_script(topic: dict, retries: int = 3, used_titles: list = None) -> dict:
    """
    Generate a factual 35-50s script for a trending topic from trend_agent.
    `topic` has keys: title, premise, hook_angle, category="trending".
    Returns the same schema as generate_story_script.
    """
    prompt = TREND_TEMPLATE.format(
        title=topic["title"],
        premise=topic["premise"],
        hook_angle=topic.get("hook_angle", ""),
    ) + _avoid_block(used_titles)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating trend script for '%s' via Claude (attempt %d)...",
                     topic["title"], attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=768,
                system=TREND_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            result = json.loads(message.content[0].text.strip())

            for key in ("topic", "hook", "script", "keywords"):
                if key not in result:
                    raise ValueError(f"Missing key '{key}' in Claude response")

            result.setdefault("on_screen_hook", result["hook"][:40].upper())
            log.info("Trend script generated: '%s'", result["topic"])
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Trend script generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Trend script generation failed after {retries} attempts")
