"""
Generates YouTube SEO metadata (title, description, hashtags) using Claude.

Pulls real tags and hashtags from the top-viewed cricket highlight videos on
YouTube first, then passes them to Claude so the output matches what's already
ranking — giving each upload the best possible SEO from day one.

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

from agents.trending_tags_agent import get_trending_tags
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from utils.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You are a viral YouTube Shorts growth expert in 2025. You have studied the top 0.1% of Shorts channels and know exactly what titles, hooks, and tags drive algorithmic push and high CTR.
Your titles must be so compelling that viewers stop scrolling immediately.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

SEO_TEMPLATE = """Generate maximum-CTR YouTube Shorts metadata for this video.

Topic: {topic}
Hook (opening line): {hook}

TOP-VIEWED videos in this niche use these tags and hashtags — copy their style:
Trending tags: {trending_tags}
Trending hashtags: {trending_hashtags}

TITLE rules (this is the #1 factor for views):
- 45-58 characters max (shorter titles get more impressions on mobile)
- PROVEN high-CTR formats — pick the best fit:
    • "Nobody expected [player/team] to do THIS 😱"
    • "[N] cricket moments that broke the internet 🤯"
    • "The moment [player] changed cricket forever"
    • "When [team] shocked the entire stadium"
    • "This [shot/wicket/catch] is statistically impossible"
    • "[Player] just did something no one has EVER done"
- Use ONE emoji (😱 🤯 💥 🔥 👀) — at the END only
- Start with a strong noun or verb — never start with "The" or "A"
- Never use ALL-CAPS

DESCRIPTION rules:
- Line 1: restate the hook with more urgency (different words)
- Lines 2-3: why this moment is historic — add a specific detail (score, year, player name)
- Line 4: "Follow for daily cricket highlights."
- End with: #Shorts

TAGS (plain English, no #, exactly 20):
- Start with the 10 most relevant trending tags above
- Add 10 specific to this exact moment/match/player
- Mix: player name, team name, tournament, year, action type

HASHTAGS (with #, exactly 5):
- Always include #Shorts and #Cricket
- Use 3 from the trending hashtags list above

Return ONLY this JSON:
{{
  "title": "...",
  "description": "...",
  "tags": ["tag1", ...],
  "hashtags": ["#Shorts", "#Cricket", "#tag3", "#tag4", "#tag5"]
}}"""


def generate_seo(topic: str, hook: str, niche: str = "cricket", trend_data: dict = None, retries: int = 3) -> dict:
    """
    Fetch trending tags (cricket only) then call Claude to generate SEO metadata.
    For non-cricket niches, trending tag lookup is skipped.
    Returns a dict with keys: title, description, tags, hashtags.
    trend_data: optional output of trend_analyzer.analyze_top_videos(); when
    provided, tags/hashtags are taken directly from the most-viewed videos.
    """
    # Step 1: determine trending tags source
    if trend_data and trend_data.get("tags"):
        trending_tags_str = ", ".join(trend_data["tags"][:20])
        trending_hashtags_str = ", ".join(trend_data["hashtags"][:8])
        log.info("Using trend_data tags from top-viewed videos")
    elif niche == "cricket":
        log.info("Fetching trending tags from top cricket highlight videos...")
        trending = get_trending_tags(topic)
        trending_tags_str = ", ".join(trending["tags"]) if trending["tags"] else "cricket highlights, cricket match, cricket shorts, cricket 2025"
        trending_hashtags_str = ", ".join(trending["hashtags"]) if trending["hashtags"] else "#Cricket, #Shorts, #CricketHighlights"
    else:
        trending_tags_str = "shorts, viral, trending, youtube shorts, 2025"
        trending_hashtags_str = "#Shorts, #Viral, #Trending"
        log.info("Skipping trending tags lookup for niche '%s'", niche)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = SEO_TEMPLATE.format(
        topic=topic,
        hook=hook,
        trending_tags=trending_tags_str,
        trending_hashtags=trending_hashtags_str,
    )

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

            # Cap to safe limits (tags allow up to 500 chars total; keep 20 + 2 brand)
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
