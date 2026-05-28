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

SYSTEM_PROMPT = """You are a top YouTube Shorts SEO strategist in 2025 specialising in viral short-form video content.
You write titles and descriptions that maximise click-through rate and watch time.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

SEO_TEMPLATE = """Generate high-performing YouTube Shorts SEO metadata for this video.

Topic: {topic}
Hook (opening line): {hook}

Here are the tags and hashtags currently used by the TOP-VIEWED videos on YouTube in this niche.
Use these as your primary source — they are proven to rank:

Trending tags from top videos:
{trending_tags}

Trending hashtags from top videos:
{trending_hashtags}

TITLE rules:
- 50-60 characters max
- Mention the key topic, player, or moment if known
- Use a curiosity gap or bold claim (e.g. "Nobody saw this coming", "This changed everything")
- You MAY use ONE emoji at the start or end for visual pop
- No ALL-CAPS words

DESCRIPTION rules:
- 4-5 sentences total
- Sentence 1: restate the hook in different words to reinforce curiosity
- Sentences 2-3: expand on why this moment is historic or dramatic
- Sentence 4: soft CTA — "Follow for more."
- End the description with: #Shorts

TAGS rules (plain English, no #):
- Return exactly 20 tags
- PRIORITISE the trending tags listed above — include as many as are relevant
- Add topic-specific tags for this exact match/moment
- Mix broad with specific

HASHTAGS rules:
- Return exactly 5 hashtags (with #)
- PRIORITISE the trending hashtags listed above
- Always include #Shorts
- Add 1-2 specific to this topic or moment

Return ONLY this JSON:
{{
  "title": "...",
  "description": "...",
  "tags": ["tag1", ...],
  "hashtags": ["#Shorts", "#tag2", "#tag3", "#tag4", "#tag5"]
}}"""


def generate_seo(topic: str, hook: str, niche: str = "cricket", retries: int = 3) -> dict:
    """
    Fetch trending tags (cricket only) then call Claude to generate SEO metadata.
    For non-cricket niches, trending tag lookup is skipped.
    Returns a dict with keys: title, description, tags, hashtags.
    """
    # Step 1: pull real trending tags from top-viewed YouTube videos (cricket only)
    if niche == "cricket":
        log.info("Fetching trending tags from top cricket highlight videos...")
        trending = get_trending_tags(topic)
        trending_tags_str = ", ".join(trending["tags"]) if trending["tags"] else "cricket highlights, cricket match, cricket shorts, cricket 2025"
        trending_hashtags_str = ", ".join(trending["hashtags"]) if trending["hashtags"] else "#Cricket, #Shorts, #CricketHighlights, #CricketLovers"
    else:
        log.info("Skipping trending tags lookup for niche '%s'", niche)
        trending_tags_str = ""
        trending_hashtags_str = ""

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

            # Enforce #Shorts always present
            if "#Shorts" not in result["hashtags"]:
                result["hashtags"].insert(0, "#Shorts")

            # Cap to safe limits
            result["hashtags"] = result["hashtags"][:5]
            result["tags"] = result["tags"][:20]

            log.info("SEO title: '%s'", result["title"])
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("SEO generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"SEO generation failed after {retries} attempts")
