"""
Generates a ~2-minute YouTube video script for a fixed story topic using Claude.

Each call takes one entry from story_topics.STORY_TOPICS (title + premise +
category) and asks Claude to turn it into a structured narrative script of
approximately 300-350 words (≈ 2 minutes of narration at natural pace).

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

STORY_SYSTEM_PROMPT = """You are a viral YouTube video writer with multiple 1M+ view videos.
Your scripts run about 2 minutes, open with a hook that stops the scroll, build tension through
a compelling narrative arc, and land a memorable twist or payoff at the end.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

STORY_TEMPLATE = """Write a compelling ~2-minute YouTube story script based on this concept:

Category: {category}
Title: {title}
Premise: {premise}

CRITICAL RULES:
- Total spoken length: ~2 minutes (~300-350 words)
- Structure:
    HOOK (first 10-15 words, second-person "you", instantly gripping)
    → BUILD (develop the scenario over 3-4 paragraphs, each raising tension or adding detail)
    → CLIMAX (the most intense or surprising moment, 1-2 paragraphs)
    → TWIST/PAYOFF (final 2-3 sentences — the scare, laugh, revelation, or emotional gut-punch)
- Write in vivid present tense, second person ("you walk in", "you hear", "you realize")
- Each paragraph should be 2-4 sentences and feel like a scene
- The "on_screen_hook" field is the EXACT text displayed as a large caption — max 6 words, ALL CAPS
- Do not end with a generic CTA like "follow for more" unless it fits naturally

Return ONLY this JSON (no markdown):
{{
  "topic": "{title}",
  "hook": "the opening hook line (10-15 words, second person)",
  "on_screen_hook": "VERY SHORT ON-SCREEN TEXT (max 6 words, ALL CAPS)",
  "script": "full ~300-350 word script including hook, build, climax, and twist",
  "keywords": ["5 to 8 vivid visual keywords for scene image generation"]
}}"""


def _avoid_block(used_titles: list = None) -> str:
    if not used_titles:
        return ""
    recent = used_titles[-20:]
    return ("\n\nALREADY USED TITLES (do NOT repeat or closely paraphrase any of these):\n" +
            "\n".join(f"  - {t}" for t in recent))


def generate_story_script(topic: dict, retries: int = 3, used_titles: list = None) -> dict:
    """
    Generate a ~2-minute YouTube video script for a fixed story topic.
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
                max_tokens=1200,
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
