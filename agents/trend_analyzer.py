"""
Finds the top-viewed cricket Shorts on YouTube via yt-dlp and extracts:
  - The most-used tags and hashtags (for SEO cloning)
  - Title hook patterns (for script generation)
  - General content patterns (format, style)

No YouTube API key needed — yt-dlp handles the search.
"""
import json
import re
import subprocess
import time
from collections import Counter
from pathlib import Path

from utils.logger import get_logger

log = get_logger(__name__)

TOP_VIEW_QUERIES = [
    "cricket highlights shorts 2025",
    "cricket moments shorts viral",
    "cricket best shots shorts",
    "india cricket shorts highlights",
]

def _fetch_top_videos(query: str, count: int = 15) -> list[dict]:
    """Fetch metadata for top videos (no download). Returns list of video dicts."""
    cmd = [
        "yt-dlp",
        f"ytsearch{count}:{query}",
        "--dump-json",
        "--no-download",
        "--no-playlist",
        "--quiet",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        videos = []
        for line in result.stdout.strip().splitlines():
            try:
                videos.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return videos
    except Exception as exc:
        log.warning("Trend fetch error for '%s': %s", query, exc)
    return []


def analyze_top_videos(max_videos: int = 30) -> dict:
    """
    Search for top cricket Shorts, aggregate their tags, hashtags, and title hooks.
    Returns:
        {
          "tags": ["tag1", ...],        # top 20 most common tags
          "hashtags": ["#tag", ...],    # top 8 hashtags (always includes #Shorts #Cricket)
          "hooks": ["hook1", ...],      # top title hook phrases
          "top_title": "...",           # title of the highest-view video found
          "top_views": 0,               # view count of that video
        }
    """
    all_videos: list[dict] = []

    for query in TOP_VIEW_QUERIES:
        log.info("Fetching trending data for: '%s'", query)
        videos = _fetch_top_videos(query, count=15)
        all_videos.extend(videos)
        time.sleep(0.5)

    if not all_videos:
        log.warning("No trend data fetched — returning empty")
        return {"tags": [], "hashtags": [], "hooks": [], "top_title": "", "top_views": 0}

    # Sort by view count descending, deduplicate by video ID
    seen_ids = set()
    unique_videos = []
    for v in sorted(all_videos, key=lambda x: x.get("view_count") or 0, reverse=True):
        vid = v.get("id", "")
        if vid and vid not in seen_ids:
            seen_ids.add(vid)
            unique_videos.append(v)

    top_videos = unique_videos[:max_videos]

    # Collect tags
    tag_counter: Counter = Counter()
    hashtag_counter: Counter = Counter()
    hook_phrases: list[str] = []

    for v in top_videos:
        # Plain tags from metadata
        for tag in (v.get("tags") or []):
            tag_counter[tag.lower().strip()] += 1
        # Hashtags from description
        desc = v.get("description") or ""
        for ht in re.findall(r"#\w+", desc):
            hashtag_counter[ht.lower()] += 1
        # Also extract from title as hook
        title = v.get("title", "")
        if title:
            hook_phrases.append(title)

    top_tags = [t for t, _ in tag_counter.most_common(20)]
    top_hashtags = [h for h, _ in hashtag_counter.most_common(10)]

    # Ensure #shorts and #cricket always present
    must_have = ["#shorts", "#cricket"]
    for mh in must_have:
        if mh not in top_hashtags:
            top_hashtags.insert(0, mh)
    top_hashtags = top_hashtags[:8]

    best = top_videos[0] if top_videos else {}

    log.info(
        "Trend analysis: %d videos, top=%s (%s views), %d tags, %d hashtags",
        len(top_videos),
        best.get("title", "")[:40],
        best.get("view_count", 0),
        len(top_tags),
        len(top_hashtags),
    )

    return {
        "tags":      top_tags,
        "hashtags":  top_hashtags,
        "hooks":     hook_phrases[:10],
        "top_title": best.get("title", ""),
        "top_views": best.get("view_count", 0),
    }
