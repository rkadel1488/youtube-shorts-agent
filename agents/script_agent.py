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


KIDS_SYSTEM_PROMPT = """You are a cheerful children's educational content creator who makes
engaging, age-appropriate videos for kids aged 3-8. Your scripts are simple, fun, and full of
wonder. Use easy vocabulary, short sentences, and a warm encouraging tone.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

KIDS_TEMPLATE = """Write a fun ~2-minute educational video script for young children (ages 3-8).

Category: {category}
Topic: {title}
Learning Goal: {premise}

CRITICAL RULES:
- Total spoken length: ~2 minutes (~200-250 words, shorter sentences for kids)
- Simple vocabulary — no words above a 2nd grade reading level
- Warm, enthusiastic, encouraging tone ("Wow!", "Let's find out!", "Amazing!")
- Structure:
    HELLO/HOOK (greet kids, ask a fun question to grab attention)
    → EXPLORE (3-4 short paragraphs, each teaching one fun fact or idea)
    → FUN ACTIVITY (one simple thing kids can try at home)
    → GOODBYE (friendly sign-off with positive encouragement)
- The "on_screen_hook" field is the EXACT text displayed as a large caption — max 5 words, ALL CAPS
- No scary, sad, or violent content — keep it 100% positive and age-appropriate

Return ONLY this JSON (no markdown):
{{
  "topic": "{title}",
  "hook": "the opening greeting/question (10-15 words, warm and friendly)",
  "on_screen_hook": "SHORT ON-SCREEN TEXT (max 5 words, ALL CAPS)",
  "script": "full ~200-250 word script for kids, simple and fun",
  "keywords": ["4 to 6 colourful visual keywords for scene image/video generation"]
}}"""


def generate_animated_kids_script(storyboard: dict, retries: int = 3) -> dict:
    """
    Generate a voiceover script from a storyboard — concatenates narration lines
    into a single flowing script with a warm narrator intro and outro.
    Returns dict with: topic, hook, on_screen_hook, script, keywords.
    """
    scenes = storyboard.get("scenes", [])
    narrations = [s.get("narration", "") for s in scenes if s.get("narration")]
    full_narration = " ".join(narrations)
    title = storyboard.get("title", "")
    character = storyboard.get("character", "a friendly animal friend")

    prompt = f"""We have a children's animated video called "{title}" featuring {character}.
Here is the scene-by-scene narration already written:

{full_narration}

Your job: rewrite this as a smooth, warm, flowing voiceover script for a friendly narrator.
- Keep the same facts and story beats but make transitions between scenes natural
- Add a warm opening ("Hello little learners! Today we're going to discover...")
- Add an encouraging closing ("Great job learning today! See you next time!")
- Keep vocabulary simple (ages 3-8), short sentences, enthusiastic tone
- Total: ~200-240 words

Return ONLY this JSON:
{{
  "topic": "{title}",
  "hook": "the opening greeting sentence (10-15 words)",
  "on_screen_hook": "SHORT CAPS TEXT (max 5 words)",
  "script": "the full polished voiceover script",
  "keywords": ["4-6 visual keywords describing the scenes"]
}}"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    for attempt in range(1, retries + 1):
        try:
            log.info("Generating animated kids voiceover script (attempt %d)...", attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=900,
                system=KIDS_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            result = json.loads(raw)
            for key in ("topic", "hook", "script", "keywords"):
                if key not in result:
                    raise ValueError(f"Missing key '{key}'")
            result.setdefault("on_screen_hook", result["hook"][:30].upper())
            log.info("Animated kids script ready: '%s'", result["topic"])
            return result
        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Animated kids script error on attempt %d: %s", attempt, exc)
        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Animated kids script generation failed after {retries} attempts")


def generate_kids_script(topic: dict, retries: int = 3) -> dict:
    """
    Generate a ~2-minute children's educational video script.
    `topic` is one entry from kids_topics.KIDS_TOPICS (id, category, title, premise).
    Returns a dict with keys: topic, hook, on_screen_hook, script, keywords.
    """
    prompt = KIDS_TEMPLATE.format(
        category=topic["category"], title=topic["title"], premise=topic["premise"],
    )
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating kids script for '%s' via Claude (attempt %d)...",
                     topic["title"], attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1000,
                system=KIDS_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            result = json.loads(raw)

            for key in ("topic", "hook", "script", "keywords"):
                if key not in result:
                    raise ValueError(f"Missing key '{key}' in Claude response")

            result.setdefault("on_screen_hook", result["hook"][:30].upper())
            log.info("Kids script generated [#%d %s]: '%s'",
                     topic["id"], topic["category"], result["topic"])
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Kids script generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Kids script generation failed after {retries} attempts")


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
