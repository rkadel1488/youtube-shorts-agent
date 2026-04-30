"""
Generates YouTube SEO metadata (title, description, hashtags) using Claude.

Output schema (JSON):
{
  "title": "...",
  "description": "...",
  "tags": ["tag1", "tag2", ...],       # plain words, no #
  "hashtags": ["#tag1", "#tag2", ...]  # 10 hashtags with #
}
"""
import json
import time

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from utils.logger import get_logger

log = get_logger(__name__)
_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a YouTube SEO specialist who writes titles and descriptions
that maximise click-through rate and watch time for Shorts.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

SEO_TEMPLATE = """Generate YouTube Shorts SEO metadata for this script.

Niche: {niche_label}
Topic: {topic}
Script excerpt: {hook}

Rules:
- Title: curiosity/shock style, under 60 chars, NO emoji, no ALL-CAPS words
- Description: 2 sentences expanding the hook. End with #Shorts
- Tags: 10 plain English keyword phrases (no #), mix broad + niche-specific
- Hashtags: exactly 10 hashtags (with #). Always include #Shorts and #viral

Return ONLY this JSON:
{{
  "title": "...",
  "description": "...",
  "tags": ["tag1", ...],
  "hashtags": ["#tag1", ...]
}}"""


def generate_seo(niche: dict, topic: str, hook: str, retries: int = 3) -> dict:
    """
    Call Claude to generate SEO metadata.
    Returns a dict with keys: title, description, tags, hashtags.
    """
    prompt = SEO_TEMPLATE.format(
        niche_label=niche["label"],
        topic=topic,
        hook=hook,
    )

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating SEO metadata (attempt %d)…", attempt)
            message = _client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            result = json.loads(raw)

            for key in ("title", "description", "tags", "hashtags"):
                if key not in result:
                    raise ValueError(f"Missing key '{key}' in SEO response")

            # Ensure #Shorts is always present
            if "#Shorts" not in result["hashtags"]:
                result["hashtags"].insert(0, "#Shorts")

            log.info("SEO title: '%s'", result["title"])
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("SEO generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"SEO generation failed after {retries} attempts")
