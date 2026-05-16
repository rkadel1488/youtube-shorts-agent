"""
Generates YouTube SEO metadata (title, description, hashtags) using Claude.

Output schema (JSON):
{
  "title": "...",
  "description": "...",
  "tags": ["tag1", "tag2", ...],       # plain words, no #
  "hashtags": ["#tag1", "#tag2", ...]  # 3-5 hashtags with #
}
"""
import json
import time

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from utils.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You are a top YouTube Shorts SEO strategist in 2025.
You write titles and descriptions that maximise click-through rate, completion rate, and watch time.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

SEO_TEMPLATE = """Generate high-performing YouTube Shorts SEO metadata for this video.

Topic: {topic}
Hook (opening line): {hook}

TITLE rules:
- 50–60 characters max
- Use a curiosity gap OR bold claim formula (e.g. "Nobody talks about...", "This changed everything", "You've been lied to about...")
- You MAY use ONE emoji at the start or end for visual pop in the feed
- No ALL-CAPS words, no clickbait that doesn't match the content

DESCRIPTION rules:
- 4–5 sentences total
- Sentence 1: restate the hook in different words to reinforce curiosity
- Sentence 2–3: expand on why this story/fact is shocking or important
- Sentence 4: soft CTA — "Follow for more stories like this every day."
- End with: #Shorts

TAGS rules (plain English, no #):
- Exactly 15 tags
- Mix: 3 broad (e.g. "amazing facts"), 7 niche-specific (e.g. "history facts shorts"), 5 ultra-specific to this exact topic
- Use phrases people actually search for on YouTube

HASHTAGS rules:
- Exactly 4 hashtags (including #)
- Always include #Shorts
- 1 broad niche tag (e.g. #Facts or #History)
- 1 topic-specific tag
- 1 trending discovery tag (e.g. #viral or #didyouknow)

Return ONLY this JSON:
{{
  "title": "...",
  "description": "...",
  "tags": ["tag1", ...],
  "hashtags": ["#Shorts", "#tag2", "#tag3", "#tag4"]
}}"""


def generate_seo(topic: str, hook: str, retries: int = 3) -> dict:
    """
    Call Claude to generate SEO metadata.
    Returns a dict with keys: title, description, tags, hashtags.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = SEO_TEMPLATE.format(topic=topic, hook=hook)

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating SEO metadata (attempt %d)…", attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=700,
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

            # Cap hashtags at 5 max
            result["hashtags"] = result["hashtags"][:5]

            log.info("SEO title: '%s'", result["title"])
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("SEO generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"SEO generation failed after {retries} attempts")
