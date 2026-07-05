"""
Fetches live trending topics and picks the best one for a factual Short.

Sources (both keyless):
  - Google Trends daily RSS  → trend name + real news headlines/snippets
  - Reddit r/popular hot     → post titles

Claude then selects the safest/strongest candidate and writes a grounded
premise using ONLY the provided headlines (no invented facts), returning a
topic dict shaped like a story_topics entry:

  {"id": 0, "category": "trending", "title": "...", "premise": "..."}
"""
import json
import os
import time
import xml.etree.ElementTree as ET

import anthropic
import requests

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from utils.logger import get_logger

log = get_logger(__name__)

TREND_REGION = os.getenv("TREND_REGION", "US")
UA = {"User-Agent": "Mozilla/5.0 (compatible; shorts-agent/1.0)"}

PICK_SYSTEM_PROMPT = """You pick topics for factual, advertiser-friendly YouTube Shorts and write premises.
You NEVER invent facts — premises must only restate information present in the provided headlines/snippets.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

PICK_TEMPLATE = """Here are topics currently trending, with real news context where available:

{candidates}

Recently covered topics (do NOT pick these or near-duplicates):
{recent}

Pick the ONE best topic for a ~45-second factual YouTube Short.

HARD REJECTIONS (never pick, regardless of traffic):
- Deaths, tragedies, crime victims, active disasters, divisive politics, anything advertiser-unfriendly
- Topics needing copyrighted footage to make sense (sports game highlights, movie/TV scenes, music videos)
- Topics whose provided headlines are too thin to support 45 seconds of specific content (a topic with zero attached headlines is automatically too thin)
- Anything in this EXCLUDED list (already rejected as duplicates): {excluded}

CATEGORY VALUE TIERS (higher tier ALWAYS beats higher traffic):
- TIER 1: AI/tech, science, space, money/economy/markets, world records, discoveries, big product launches
- TIER 2: health breakthroughs, nature/animals, viral internet phenomena, gaming industry news
- TIER 3: entertainment/celebrity — pick ONLY if no Tier 1 or Tier 2 candidate passes the rules

SELECTION: take the highest tier that has a passing candidate; within that tier, take the HIGHEST search_traffic.

PREMISE: a 2-4 sentence factual summary built ONLY from the provided headlines/snippets. Do not add numbers, names, or claims that are not in them.

Return ONLY this JSON:
{{
  "title": "short topic name",
  "premise": "2-4 sentence factual summary from the headlines only",
  "category": "trending",
  "hook_angle": "one sentence: the most surprising angle to open with"
}}"""


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_traffic(text: str) -> int:
    """'200,000+' -> 200000; '1M+' -> 1000000."""
    t = text.strip().replace(",", "").replace("+", "").upper()
    try:
        if t.endswith("M"):
            return int(float(t[:-1]) * 1_000_000)
        if t.endswith("K"):
            return int(float(t[:-1]) * 1_000)
        return int(t)
    except ValueError:
        return 0


_STOPWORDS = {"the", "a", "an", "of", "in", "on", "for", "to", "and", "is", "at", "vs", "new"}


def _norm_tokens(text: str) -> set:
    words = "".join(c.lower() if c.isalnum() or c.isspace() else " " for c in text).split()
    return {w for w in words if w not in _STOPWORDS}


def is_duplicate(title: str, recent_topics: list) -> bool:
    """True if title is the same as / highly overlapping with any recent topic."""
    a = _norm_tokens(title)
    if not a:
        return False
    for prev in recent_topics or []:
        b = _norm_tokens(prev)
        if not b:
            continue
        overlap = len(a & b) / min(len(a), len(b))
        if overlap >= 0.6:
            return True
    return False


# ── trend sources ─────────────────────────────────────────────────────────────

def fetch_google_trends(max_items: int = 12) -> list[dict]:
    """Daily trends RSS with attached news headlines + snippets."""
    try:
        r = requests.get(
            f"https://trends.google.com/trending/rss?geo={TREND_REGION}",
            headers=UA, timeout=15,
        )
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        for item in root.iter("item"):
            entry = {"trend": "", "search_traffic": 0, "news": []}
            for el in item.iter():
                tag = el.tag.split("}")[-1]
                if tag == "title" and not entry["trend"]:
                    entry["trend"] = (el.text or "").strip()
                elif tag == "approx_traffic" and el.text:
                    entry["search_traffic"] = _parse_traffic(el.text)
                elif tag == "news_item_title" and el.text:
                    entry["news"].append({"headline": el.text.strip()})
                elif tag == "news_item_snippet" and el.text and entry["news"]:
                    entry["news"][-1]["snippet"] = el.text.strip()
            if entry["trend"]:
                items.append(entry)
        # highest search traffic first
        items.sort(key=lambda e: e["search_traffic"], reverse=True)
        items = items[:max_items]
        log.info("Google Trends: %d items (top traffic: %s)",
                 len(items), items[0]["search_traffic"] if items else 0)
        return items
    except Exception as exc:
        log.warning("Google Trends fetch failed: %s", exc)
        return []


def fetch_reddit_hot(max_items: int = 15) -> list[dict]:
    try:
        r = requests.get(
            f"https://www.reddit.com/r/popular/hot.json?limit={max_items}",
            headers=UA, timeout=15,
        )
        r.raise_for_status()
        posts = [
            {"trend": c["data"]["title"], "news": [],
             "source": f"r/{c['data'].get('subreddit', '')}"}
            for c in r.json().get("data", {}).get("children", [])
            if not c["data"].get("over_18")
        ]
        log.info("Reddit hot: %d items", len(posts))
        return posts
    except Exception as exc:
        log.warning("Reddit fetch failed: %s", exc)
        return []


# ── topic selection ───────────────────────────────────────────────────────────

def get_trend_topic(recent_topics: list = None, retries: int = 5) -> dict:
    """Fetch trends and have Claude pick one + write a grounded premise."""
    candidates = fetch_google_trends() + fetch_reddit_hot()
    if not candidates:
        raise RuntimeError("All trend sources failed")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    excluded: list = []

    for attempt in range(1, retries + 1):
        try:
            prompt = PICK_TEMPLATE.format(
                candidates=json.dumps(candidates, indent=1, ensure_ascii=False),
                recent=json.dumps((recent_topics or [])[-40:], ensure_ascii=False),
                excluded=json.dumps(excluded, ensure_ascii=False),
            )
            log.info("Selecting trend topic via Claude (attempt %d)...", attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=512,
                system=PICK_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            result = json.loads(message.content[0].text.strip())
            for key in ("title", "premise"):
                if not result.get(key):
                    raise ValueError(f"Missing '{key}' in Claude response")
            # HARD dedupe: never allow a repeat, even if Claude ignores the prompt
            if is_duplicate(result["title"], (recent_topics or []) + excluded):
                log.warning("Duplicate topic '%s' — excluding and retrying", result["title"])
                excluded.append(result["title"])
                continue
            topic = {
                "id": 0,
                "category": "trending",
                "title": result["title"],
                "premise": result["premise"],
                "hook_angle": result.get("hook_angle", ""),
            }
            log.info("Trend topic selected: %s (traffic-ranked)", topic["title"])
            return topic
        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Trend selection error on attempt %d: %s", attempt, exc)
        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Trend topic selection failed after {retries} attempts")


# ── evergreen fallback (used when all trend sources are down) ─────────────────

EVERGREEN_SYSTEM_PROMPT = """You generate topics for factual YouTube Shorts about well-established, widely documented facts.
You only use facts that are thoroughly verified and part of common documented knowledge (science, space,
technology, nature, records, how things work). Nothing speculative, nothing recent, nothing contested.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

EVERGREEN_TEMPLATE = """Generate ONE surprising factual topic for a ~45-second YouTube Short.

Rules:
- Must be a well-established, easily verifiable fact (science, space, tech, nature, human body, records)
- Must have a genuine "wait, really?" quality
- Must NOT be similar to any of these recently covered topics:
{recent}

Return ONLY this JSON:
{{
  "title": "short topic name",
  "premise": "3-4 sentence summary of the established facts",
  "category": "evergreen",
  "hook_angle": "one sentence: the most surprising angle to open with"
}}"""


def get_evergreen_topic(recent_topics: list = None, retries: int = 3) -> dict:
    """Fallback topic from established facts when trend sources are unavailable."""
    prompt = EVERGREEN_TEMPLATE.format(
        recent=json.dumps((recent_topics or [])[-30:], ensure_ascii=False),
    )
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating evergreen fallback topic (attempt %d)...", attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=512,
                system=EVERGREEN_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            result = json.loads(message.content[0].text.strip())
            for key in ("title", "premise"):
                if not result.get(key):
                    raise ValueError(f"Missing '{key}' in Claude response")
            if is_duplicate(result["title"], recent_topics or []):
                log.warning("Duplicate evergreen topic '%s' — retrying", result["title"])
                continue
            topic = {
                "id": 0,
                "category": "evergreen",
                "title": result["title"],
                "premise": result["premise"],
                "hook_angle": result.get("hook_angle", ""),
            }
            log.info("Evergreen topic: %s", topic["title"])
            return topic
        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Evergreen topic error on attempt %d: %s", attempt, exc)
        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Evergreen topic generation failed after {retries} attempts")
