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

Pick the ONE best topic for a ~45-second factual YouTube Short, using these rules:
- REJECT: deaths, tragedies, crime victims, active disasters, divisive politics, anything advertiser-unfriendly
- REJECT: topics needing copyrighted footage to make sense (sports game highlights, movie/TV scenes, music videos)
- PREFER: tech/AI, science, space, money/economy, records, discoveries, viral internet phenomena, surprising announcements
- PREFER: topics whose provided headlines contain enough concrete detail to fill 45 seconds
- The premise must be a 2-4 sentence factual summary built ONLY from the provided headlines/snippets. Do not add numbers, names, or claims that are not in them.

Return ONLY this JSON:
{{
  "title": "short topic name",
  "premise": "2-4 sentence factual summary from the headlines only",
  "category": "trending",
  "hook_angle": "one sentence: the most surprising angle to open with"
}}"""


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
            entry = {"trend": "", "news": []}
            for el in item.iter():
                tag = el.tag.split("}")[-1]
                if tag == "title" and not entry["trend"]:
                    entry["trend"] = (el.text or "").strip()
                elif tag == "news_item_title" and el.text:
                    entry["news"].append({"headline": el.text.strip()})
                elif tag == "news_item_snippet" and el.text and entry["news"]:
                    entry["news"][-1]["snippet"] = el.text.strip()
            if entry["trend"]:
                items.append(entry)
            if len(items) >= max_items:
                break
        log.info("Google Trends: %d items", len(items))
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

def get_trend_topic(recent_topics: list = None, retries: int = 3) -> dict:
    """Fetch trends and have Claude pick one + write a grounded premise."""
    candidates = fetch_google_trends() + fetch_reddit_hot()
    if not candidates:
        raise RuntimeError("All trend sources failed")

    prompt = PICK_TEMPLATE.format(
        candidates=json.dumps(candidates, indent=1, ensure_ascii=False),
        recent=json.dumps((recent_topics or [])[-30:], ensure_ascii=False),
    )
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    for attempt in range(1, retries + 1):
        try:
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
            topic = {
                "id": 0,
                "category": "trending",
                "title": result["title"],
                "premise": result["premise"],
                "hook_angle": result.get("hook_angle", ""),
            }
            log.info("Trend topic selected: %s", topic["title"])
            return topic
        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Trend selection error on attempt %d: %s", attempt, exc)
        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Trend topic selection failed after {retries} attempts")
