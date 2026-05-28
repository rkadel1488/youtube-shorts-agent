"""
Fetches tags and hashtags from the top-viewed cricket highlight videos on YouTube.
Uses the existing OAuth credentials so no extra API key is needed.

Strategy:
  1. Search YouTube for cricket highlight videos matching the current topic
  2. Fetch the top results sorted by view count
  3. Extract their tags and description hashtags
  4. Return the most frequently used ones for SEO reuse
"""
import json
import re
import time
from collections import Counter
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import YOUTUBE_CLIENT_SECRETS_FILE, YOUTUBE_SCOPES, YOUTUBE_TOKEN_FILE
from utils.logger import get_logger

log = get_logger(__name__)

# Broad search terms always included so we find cricket-specific content
BASE_CRICKET_QUERIES = [
    "cricket highlights today",
    "cricket match highlights",
]


def _get_youtube():
    """Build a YouTube API client using saved OAuth credentials."""
    token_path = Path(YOUTUBE_TOKEN_FILE)
    if not token_path.exists():
        log.warning("YouTube token not found — skipping trending tags fetch")
        return None
    try:
        with open(token_path) as f:
            creds = Credentials.from_authorized_user_info(json.load(f), YOUTUBE_SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return build("youtube", "v3", credentials=creds)
    except Exception as exc:
        log.warning("Could not build YouTube client: %s", exc)
        return None


def _search_video_ids(youtube, query: str, max_results: int = 10) -> list[str]:
    """Search YouTube for cricket highlight videos and return video IDs."""
    try:
        resp = youtube.search().list(
            q=query,
            part="id",
            type="video",
            videoDuration="short",
            order="viewCount",
            maxResults=max_results,
            relevanceLanguage="en",
        ).execute()
        return [item["id"]["videoId"] for item in resp.get("items", []) if "videoId" in item["id"]]
    except Exception as exc:
        log.warning("YouTube search failed for '%s': %s", query, exc)
        return []


def _get_video_tags(youtube, video_ids: list[str]) -> tuple[list[str], list[str]]:
    """
    Fetch snippet (tags, description) for a list of video IDs.
    Returns (tags_list, hashtags_list) aggregated across all videos.
    """
    if not video_ids:
        return [], []
    try:
        resp = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(video_ids),
        ).execute()
    except Exception as exc:
        log.warning("YouTube videos.list failed: %s", exc)
        return [], []

    all_tags: list[str] = []
    all_hashtags: list[str] = []

    for item in resp.get("items", []):
        snippet = item.get("snippet", {})
        # Plain tags from snippet
        all_tags.extend(snippet.get("tags", []))
        # Hashtags from description
        desc = snippet.get("description", "")
        all_hashtags.extend(re.findall(r"#\w+", desc))

    return all_tags, all_hashtags


def get_trending_tags(topic: str, max_tags: int = 20, max_hashtags: int = 8) -> dict:
    """
    Search YouTube for top cricket highlight videos similar to *topic*,
    extract their tags and hashtags, and return the most popular ones.

    Returns:
        {
            "tags": ["tag1", "tag2", ...],       # top plain tags
            "hashtags": ["#tag1", "#tag2", ...]  # top hashtags incl. #Shorts
        }
    """
    youtube = _get_youtube()
    if not youtube:
        return {"tags": [], "hashtags": []}

    # Build search queries from topic + base cricket terms
    queries = [f"{topic} cricket highlights"] + BASE_CRICKET_QUERIES

    all_tags: list[str] = []
    all_hashtags: list[str] = []

    for query in queries[:2]:  # limit to 2 searches to save quota
        video_ids = _search_video_ids(youtube, query, max_results=10)
        tags, hashtags = _get_video_tags(youtube, video_ids)
        all_tags.extend(tags)
        all_hashtags.extend(hashtags)
        time.sleep(0.5)

    # Count frequency and pick top N (lowercase for dedup)
    tag_counter = Counter(t.lower().strip() for t in all_tags if t.strip())
    hashtag_counter = Counter(h.lower().strip() for h in all_hashtags if h.strip())

    top_tags = [tag for tag, _ in tag_counter.most_common(max_tags)]
    top_hashtags = [ht for ht, _ in hashtag_counter.most_common(max_hashtags)]

    # Always ensure #Shorts is present
    shorts = "#shorts"
    if shorts not in [h.lower() for h in top_hashtags]:
        top_hashtags.insert(0, "#Shorts")

    log.info("Trending tags found: %d tags, %d hashtags", len(top_tags), len(top_hashtags))
    return {"tags": top_tags, "hashtags": top_hashtags}
