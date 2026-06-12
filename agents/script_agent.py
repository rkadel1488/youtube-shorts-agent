"""
Generates a YouTube Shorts cricket highlight script using Claude.

Fetches real recent match data first, then asks Claude to write
an exciting highlight commentary script based on that data.

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
import random
import time

import anthropic

from agents.cricket_agent import get_recent_matches
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from utils.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You are a viral cricket Shorts creator whose videos consistently hit 1M+ views.
You know that 70% of Shorts viewers watch silently, so the HOOK must work as on-screen text too.
Your hooks are short, visual, and create instant FOMO or disbelief.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

SCRIPT_TEMPLATE = """Write a viral YouTube Shorts cricket highlight script based on this match data:

{match_info}

CRITICAL RULES:
- Total spoken length: 18-25 seconds (~50-70 words) — shorter = higher completion rate
- Hook (first line, MAX 8 words): must work as BOTH spoken audio AND on-screen text.
  Use shock/disbelief/FOMO — pick the best format:
    • "[Player] just broke a [X]-year record."
    • "Nobody expected [team] to do THIS."
    • "[Score] in the final over. Unbelievable."
    • "The [shot/ball/catch] that silenced [N] thousand fans."
    • "This only happens once in [N] years."
- Body: 3-4 punchy sentences max 8 words each. Present tense. Build to the climax.
- End with: "Follow for daily cricket highlights."
- The "on_screen_hook" field is the EXACT text displayed as a large caption — keep it under 6 words, ALL CAPS.

Return ONLY this JSON (no markdown):
{{
  "topic": "punchy title (e.g. 'India\\'s Last-Ball Six That Shocked the World')",
  "hook": "the opening hook line (max 8 words)",
  "on_screen_hook": "VERY SHORT ON-SCREEN TEXT (max 6 words, ALL CAPS)",
  "script": "full script including hook, body, and CTA",
  "keywords": ["cricket", "stadium", "batting", "bowling", "cricket match"]
}}"""

FALLBACK_TEMPLATE = """Write a viral YouTube Shorts script about a jaw-dropping cricket moment — \
a last-ball six, an unplayable delivery, or a world-record innings.

CRITICAL RULES:
- Total spoken length: 18-25 seconds (~50-70 words) — shorter = higher completion rate
- Hook (first line, MAX 8 words): creates instant shock or FOMO, works as on-screen text
- Body: 3-4 punchy sentences max 8 words each, present tense, build to climax
- End with: "Follow for daily cricket highlights."

Return ONLY this JSON (no markdown):
{{
  "topic": "punchy title that makes people stop scrolling",
  "hook": "the opening hook line (max 8 words)",
  "on_screen_hook": "VERY SHORT ON-SCREEN TEXT (max 6 words, ALL CAPS)",
  "script": "full script including hook, body, and CTA",
  "keywords": ["cricket", "stadium", "batting", "bowling", "cricket match"]
}}"""


NICHE_PROMPTS = {
    "fun_facts": """\
Write a viral mind-blowing fun fact Short script.

CRITICAL RULES:
- Total spoken length: 18-25 seconds (~50-70 words)
- Hook (MAX 8 words): must make the viewer say "No way!" — works as on-screen text
- Body: explains the fact in vivid terms, 3-4 punchy sentences max 8 words each
- End with: "Follow for daily mind-blowing facts."

Return ONLY this JSON (no markdown):
{{
  "topic": "short punchy title",
  "hook": "opening hook line (max 8 words)",
  "on_screen_hook": "VERY SHORT ON-SCREEN VERSION (max 6 words, ALL CAPS)",
  "script": "full script including hook, body, and CTA",
  "keywords": ["facts", "mindblow", "didyouknow", "science", "amazing"]
}}""",

    "horror_story": """\
Write a viral horror story Short script.

CRITICAL RULES:
- Total spoken length: 18-25 seconds (~50-70 words)
- Hook (MAX 8 words): spine-chilling opening that works as on-screen text
- Body: build dread fast with 3-4 punchy sentences max 8 words each
- End with a twist or scare, then: "Follow for more horror stories."

Return ONLY this JSON (no markdown):
{{
  "topic": "short punchy title",
  "hook": "opening hook line (max 8 words)",
  "on_screen_hook": "VERY SHORT ON-SCREEN VERSION (max 6 words, ALL CAPS)",
  "script": "full script including hook, body, and CTA",
  "keywords": ["horror", "scary", "creepy", "thriller", "horrortok"]
}}""",

    "football": """\
Write a viral football (soccer) highlights Short script.

CRITICAL RULES:
- Total spoken length: 18-25 seconds (~50-70 words)
- Hook (MAX 8 words): about a dramatic goal, save, or moment — works as on-screen text
- Body: build tension in 3-4 punchy sentences max 8 words each, deliver the result
- End with: "Follow for daily football highlights."
- Present tense, live commentator energy.

Return ONLY this JSON (no markdown):
{{
  "topic": "short punchy title",
  "hook": "opening hook line (max 8 words)",
  "on_screen_hook": "VERY SHORT ON-SCREEN VERSION (max 6 words, ALL CAPS)",
  "script": "full script including hook, body, and CTA",
  "keywords": ["football", "soccer", "goals", "highlights", "footballshorts"]
}}""",
}

NICHE_SYSTEM_PROMPT = """You are a viral short-form video creator for YouTube Shorts with 1M+ view videos.
Your scripts are under 25 seconds, have hooks that stop the scroll, and work for silent viewers.
Always respond with valid JSON only — no markdown fences, no extra commentary."""


def _avoid_block(used_titles: list = None, used_topics: list = None) -> str:
    """Build a prompt suffix telling Claude which titles/topics to avoid."""
    parts = []
    if used_titles:
        recent = used_titles[-20:]
        parts.append("ALREADY USED TITLES (do NOT repeat or closely paraphrase any of these):\n" +
                      "\n".join(f"  - {t}" for t in recent))
    if used_topics:
        recent = used_topics[-20:]
        parts.append("ALREADY USED TOPICS (choose a completely different subject):\n" +
                      "\n".join(f"  - {t}" for t in recent))
    if not parts:
        return ""
    return "\n\n" + "\n\n".join(parts)


def generate_niche_script(niche: str, retries: int = 3,
                          used_titles: list = None, used_topics: list = None) -> dict:
    """
    Generate an 18-25 second YouTube Shorts script for the given niche.
    Supported niches: 'fun_facts', 'horror_story', 'football'.
    Returns a dict with keys: topic, hook, on_screen_hook, script, keywords.
    """
    if niche not in NICHE_PROMPTS:
        raise ValueError(f"Unknown niche '{niche}'. Supported: {list(NICHE_PROMPTS)}")

    avoid_block = _avoid_block(used_titles, used_topics)
    prompt = NICHE_PROMPTS[niche] + avoid_block
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

            result.setdefault("on_screen_hook", result["hook"][:40].upper())
            log.info("Niche script generated [%s]: '%s'", niche, result["topic"])
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Niche script generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Niche script generation failed after {retries} attempts")


def generate_script(retries: int = 3,
                    used_titles: list = None, used_topics: list = None) -> dict:
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

    prompt += _avoid_block(used_titles, used_topics)

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

            result.setdefault("on_screen_hook", result["hook"][:40].upper())
            log.info("Script generated: '%s'", result["topic"])
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Script generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Script generation failed after {retries} attempts")


TREND_SCRIPT_TEMPLATE = """\
Here are the titles of the TOP-VIEWED cricket Short videos on YouTube right now:

{top_hooks}

Most common tags on these videos:
{top_tags}

Write a viral YouTube Shorts cricket highlight script that COPIES the hook style of these top videos.

CRITICAL RULES:
- Total spoken length: 18-25 seconds (~50-70 words) — shorter = higher completion rate
- Hook (MAX 8 words): copy the EXACT style of the top titles above — shock, disbelief, FOMO
- The "on_screen_hook" is displayed as a large caption to silent viewers — max 6 words, ALL CAPS
- Body: 3-4 punchy sentences max 8 words each, present tense, build to climax
- End with: "Follow for daily cricket highlights."

Return ONLY this JSON (no markdown):
{{
  "topic": "punchy title matching the trending style",
  "hook": "the opening hook line (max 8 words)",
  "on_screen_hook": "VERY SHORT ON-SCREEN VERSION (max 6 words, ALL CAPS)",
  "script": "full script including hook, body, and CTA",
  "keywords": ["cricket", "highlights", "shorts", "cricket2025", "cricketlovers"]
}}"""


def generate_trend_script(trend_data: dict, retries: int = 3,
                          used_titles: list = None, used_topics: list = None) -> dict:
    """
    Generate a cricket script that mimics the style of top-viewed cricket Shorts.
    trend_data: output of trend_analyzer.analyze_top_videos()
    """
    hooks = trend_data.get("hooks", [])
    tags  = trend_data.get("tags", [])

    if not hooks:
        log.info("No trend hooks available — falling back to generic script")
        return generate_script(retries=retries, used_titles=used_titles, used_topics=used_topics)

    top_hooks_str = "\n".join(f"  • {h}" for h in hooks[:5])
    top_tags_str  = ", ".join(tags[:15]) if tags else "cricket, highlights, shorts"

    prompt = TREND_SCRIPT_TEMPLATE.format(
        top_hooks=top_hooks_str,
        top_tags=top_tags_str,
    ) + _avoid_block(used_titles, used_topics)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating trend-based script (attempt %d)...", attempt)
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
                    raise ValueError(f"Missing key '{key}'")
            result.setdefault("on_screen_hook", result["hook"][:40].upper())
            log.info("Trend script generated: '%s'", result["topic"])
            return result
        except json.JSONDecodeError as exc:
            log.warning("JSON parse error attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Trend script error attempt %d: %s", attempt, exc)
        if attempt < retries:
            time.sleep(2 ** attempt)

    return generate_script(retries=retries)
