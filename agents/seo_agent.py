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

SYSTEM_PROMPT = """You are a viral YouTube growth expert in 2025. You have studied the top 0.1% of story/narrative channels and know exactly what titles, hooks, and tags drive algorithmic push and high CTR for 2-minute videos.
Your titles must be so compelling that viewers click immediately.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

SEO_TEMPLATE = """Generate maximum-CTR YouTube video metadata for this ~2-minute story video.

Topic: {topic}
Hook (opening line): {hook}

Trending tags to draw style from: {trending_tags}
Trending hashtags to draw style from: {trending_hashtags}

TITLE rules (this is the #1 factor for views):
- 50-65 characters max
- PROVEN high-CTR formats — pick the best fit:
    • "You won't believe what happens next 😱"
    • "This story will haunt you tonight 👀"
    • "Nobody saw this twist coming 🤯"
    • "I can't stop thinking about this story 💥"
    • "POV: this actually happened to someone 🔥"
    • "This 2-minute story will change how you think 👁"
- Use ONE emoji (😱 🤯 💥 🔥 👀 👁) — at the END only
- Start with a strong noun or verb — never start with "The" or "A"
- Never use ALL-CAPS

DESCRIPTION rules:
- Line 1: restate the hook with more urgency (different words)
- Lines 2-4: add vivid details that tease the story without spoiling the twist
- Line 5: "Follow for more stories like this."

TAGS (plain English, no #, exactly 25):
- Mix broad high-traffic terms + niche story-specific terms for max reach:
    BROAD (5): always include some of: story, horror story, scary story, thriller, mystery, plot twist, mind blowing, true story, scary, creepy
    GENRE (5): specific to this story's category (sci-fi, comedy, emotional, suspense, etc.)
    MOOD (5): atmospheric words — eerie, haunting, chilling, heartwarming, shocking, unexpected, dark, surreal
    THEME (5): the core concept — mirror, reflection, time loop, AI, ghost, letter, door, stranger, etc.
    VIRAL HOOKS (5): you won't believe, wait for the twist, insane ending, mind blown, must watch, viral story

HASHTAGS (with #, exactly 8):
- Always include: #StoryTime #Thriller #MysteryStory #PlotTwist
- Add 4 more specific to this story's genre/mood
- Do NOT include #Shorts

Return ONLY this JSON:
{{
  "title": "...",
  "description": "...",
  "tags": ["tag1", ...],
  "hashtags": ["#StoryTime", "#Thriller", "#MysteryStory", "#PlotTwist", "#tag5", "#tag6", "#tag7", "#tag8"]
}}"""


KIDS_SEO_TEMPLATE = """Generate YouTube video metadata for a children's educational video.

Topic: {topic}
Opening line: {hook}

TITLE rules:
- 50-65 characters max
- Child-friendly and educational, e.g.:
    • "Learn About {topic} with Fun Facts for Kids! 🌟"
    • "Amazing {topic} Facts Kids Will Love! 🎉"
    • "Let's Explore {topic} Together! Fun for Kids 🌈"
- Use ONE emoji at the END
- Never use ALL-CAPS, scary words, or clickbait

DESCRIPTION rules:
- Line 1: what kids will learn from this video
- Lines 2-4: fun highlights from the video (tease 2-3 facts)
- Line 5: "Subscribe for more fun educational videos for kids!"

TAGS (plain English, no #, exactly 20):
- Include: kids learning, educational video for kids, children's videos, fun facts for kids, learning for toddlers
- Add topic-specific terms

HASHTAGS (with #, exactly 8):
- Always include: #KidsLearn #EducationalVideo #ChildrensVideos #FunForKids
- Add 4 more matching the topic

Return ONLY this JSON:
{{
  "title": "...",
  "description": "...",
  "tags": ["tag1", ...],
  "hashtags": ["#KidsLearn", "#EducationalVideo", "#ChildrensVideos", "#FunForKids", "#tag5", "#tag6", "#tag7", "#tag8"]
}}"""


def generate_animated_kids_seo(topic: str, hook: str, retries: int = 3) -> dict:
    """Generate SEO metadata for an animated children's educational video."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""Generate YouTube metadata for a SHORT animated educational video for children (ages 3-8).

Topic: {topic}
Opening line: {hook}

TITLE rules (60 chars max):
- Child-friendly, fun, educational e.g.:
    "Learn About {topic}! 🌟 Animated Kids Video"
    "{topic} for Kids! Fun Cartoon Learning 🎨"
    "Amazing {topic} Facts! Kids Animation 🦋"
- ONE emoji at end, colourful/friendly

DESCRIPTION:
- Line 1: what kids learn
- Lines 2-3: 2 fun highlights
- Line 4: "Subscribe for more fun animated learning videos!"

TAGS (20 total, no #):
- Include: kids animation, animated educational video, cartoon for kids, learning for toddlers, kids youtube

HASHTAGS (8 total with #):
- Always: #KidsAnimation #EducationalCartoon #LearnWithMe #KidsVideos
- Add 4 topic-specific

Return ONLY JSON:
{{
  "title": "...",
  "description": "...",
  "tags": ["tag1", ...],
  "hashtags": ["#KidsAnimation", "#EducationalCartoon", "#LearnWithMe", "#KidsVideos", "#tag5", "#tag6", "#tag7", "#tag8"]
}}"""

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating animated kids SEO (attempt %d)...", attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=700,
                system="You are a children's YouTube SEO expert. Respond with valid JSON only.",
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            result = json.loads(raw)
            for key in ("title", "description", "tags", "hashtags"):
                if key not in result:
                    raise ValueError(f"Missing key '{key}'")
            for brand_tag in ("aaryankelvin", "aaryan kelvin"):
                if brand_tag not in result["tags"]:
                    result["tags"].append(brand_tag)
            if "#aaryankelvin" not in result["hashtags"]:
                result["hashtags"].append("#aaryankelvin")
            result["tags"] = result["tags"][:25]
            result["hashtags"] = result["hashtags"][:9]
            log.info("Animated kids SEO title: '%s'", result["title"])
            return result
        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Animated kids SEO error on attempt %d: %s", attempt, exc)
        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Animated kids SEO generation failed after {retries} attempts")


def generate_kids_seo(topic: str, hook: str, retries: int = 3) -> dict:
    """Generate SEO metadata for a children's educational video."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = KIDS_SEO_TEMPLATE.format(topic=topic, hook=hook)

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating kids SEO metadata (attempt %d)...", attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=800,
                system="You are a children's YouTube channel SEO expert. Always respond with valid JSON only — no markdown fences.",
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            result = json.loads(raw)

            for key in ("title", "description", "tags", "hashtags"):
                if key not in result:
                    raise ValueError(f"Missing key '{key}' in SEO response")

            for brand_tag in ("aaryankelvin", "aaryan kelvin"):
                if brand_tag not in result["tags"]:
                    result["tags"].append(brand_tag)
            if "#aaryankelvin" not in result["hashtags"]:
                result["hashtags"].append("#aaryankelvin")

            result["tags"] = result["tags"][:25]
            result["hashtags"] = result["hashtags"][:9]
            log.info("Kids SEO title: '%s'", result["title"])
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Kids SEO generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Kids SEO generation failed after {retries} attempts")


def generate_seo(topic: str, hook: str, niche: str = "story", trend_data: dict = None,
                 used_titles: list = None, retries: int = 3) -> dict:
    """
    Call Claude to generate SEO metadata for a story video.
    Returns a dict with keys: title, description, tags, hashtags.
    """
    if trend_data and trend_data.get("tags"):
        trending_tags_str = ", ".join(trend_data["tags"][:20])
        trending_hashtags_str = ", ".join(trend_data["hashtags"][:8])
    else:
        trending_tags_str = "viral, story, plot twist, trending, 2025, narrative, mystery, thriller"
        trending_hashtags_str = "#Viral, #StoryTime, #MysteryStory, #Thriller, #MindBlown"

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
                max_tokens=900,
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

            # Enforce brand hashtag always present (at end)
            if "#aaryankelvin" not in result["hashtags"]:
                result["hashtags"].append("#aaryankelvin")

            result["hashtags"] = result["hashtags"][:9]
            result["tags"] = result["tags"][:25]

            log.info("SEO title: '%s'", result["title"])
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("SEO generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"SEO generation failed after {retries} attempts")
