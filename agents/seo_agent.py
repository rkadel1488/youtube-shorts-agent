"""
Generates YouTube SEO metadata (title, description, hashtags) using Claude.

Output schema (JSON):
{
  "title": "...",
  "description": "...",
  "tags": ["tag1", "tag2", ...],       # plain words, no #
  "hashtags": ["#tag1", "#tag2", ...]  # hashtags with #
}
"""
import json
import time

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from utils.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You are a YouTube Shorts growth expert for factual news/tech/science channels. You have studied the top 0.1% of factual Shorts channels and know exactly what titles, hooks, and tags drive algorithmic push and high CTR while staying credible.
Your titles create genuine curiosity about a real event — never vague clickbait that overpromises.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

SEO_TEMPLATE = """Generate maximum-CTR YouTube Shorts metadata for this factual video about a trending topic.

Topic: {topic}
Hook (opening line): {hook}

Trending tags to draw style from: {trending_tags}
Trending hashtags to draw style from: {trending_hashtags}

TITLE rules (this is the #1 factor for views):
- 45-58 characters max (shorter titles get more impressions on mobile)
- Must reference the ACTUAL subject (a name, thing, or number from the topic) — specific beats vague
- PROVEN high-CTR formats for factual content — pick the best fit:
    • "[Subject] just changed everything 🤯"
    • "Why everyone is talking about [subject]"
    • "[Number/scale fact] — and it's real 😳"
    • "[Subject] just broke the internet"
    • "The truth about [subject]"
- Use at most ONE emoji (🤯 😳 🔥 🚨 👀) — at the END only
- Start with a strong noun or verb — never start with "The" or "A" unless using "The truth about"
- Never use ALL-CAPS, never promise what the video doesn't deliver

DESCRIPTION rules:
- Line 1: restate the hook with more urgency (different words)
- Lines 2-3: add one concrete detail from the topic that hooks readers further
- Line 4: "Follow for more trending stories."
- End with: #Shorts

TAGS (plain English, no #, exactly 20):
- Start with the 10 most relevant trending tags above
- Add 10 specific to this exact topic: names, category, related terms people search

HASHTAGS (with #, exactly 5):
- Always include #Shorts
- Prefer hashtags matching the topic's category (#Tech #AI #Science #Space #News #Money)

Return ONLY this JSON:
{{
  "title": "...",
  "description": "...",
  "tags": ["tag1", ...],
  "hashtags": ["#Shorts", "#tag2", "#tag3", "#tag4", "#tag5"]
}}"""


def generate_seo(topic: str, hook: str, niche: str = "trending news", trend_data: dict = None,
                 used_titles: list = None, retries: int = 3) -> dict:
    """
    Call Claude to generate SEO metadata for a story Short.
    Returns a dict with keys: title, description, tags, hashtags.
    trend_data: optional dict with "tags"/"hashtags" lists to steer style.
    used_titles: list of previously used titles Claude must not repeat.
    """
    if trend_data and trend_data.get("tags"):
        trending_tags_str = ", ".join(trend_data["tags"][:20])
        trending_hashtags_str = ", ".join(trend_data["hashtags"][:8])
    else:
        trending_tags_str = "shorts, viral, trending, news, breaking, tech, ai, science, 2026, explained"
        trending_hashtags_str = "#Shorts, #Viral, #Trending, #News, #Tech"

    # Build avoid-duplicate instruction
    avoid_str = ""
    if used_titles:
        recent = used_titles[-20:]
        avoid_str = (
            "\n\nIMPORTANT — do NOT use any of these previously posted titles "
            "(or anything that sounds similar):\n" +
            "\n".join(f"  - {t}" for t in recent)
        )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = SEO_TEMPLATE.format(
        topic=topic,
        hook=hook,
        trending_tags=trending_tags_str,
        trending_hashtags=trending_hashtags_str,
    ) + avoid_str

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating SEO metadata (attempt %d)...", attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=800,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            result = json.loads(raw)

            for key in ("title", "description", "tags", "hashtags"):
                if key not in result:
                    raise ValueError(f"Missing key '{key}' in SEO response")

            # Always inject brand tags
            for brand_tag in ("aaryankelvin", "aaryan kelvin"):
                if brand_tag not in result["tags"]:
                    result["tags"].append(brand_tag)

            # Enforce #Shorts and brand hashtag always present
            for brand_ht in ("#Shorts", "#aaryankelvin"):
                if brand_ht not in result["hashtags"]:
                    result["hashtags"].insert(0, brand_ht)

            result["hashtags"] = result["hashtags"][:6]
            result["tags"] = result["tags"][:22]

            log.info("SEO title: '%s'", result["title"])
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("SEO generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"SEO generation failed after {retries} attempts")
