"""
Finds and downloads Creative Commons licensed cricket Shorts from YouTube.

Uses YouTube Data API to search for CC-licensed cricket highlight Shorts,
then downloads the best match using yt-dlp.

All downloaded videos carry a Creative Commons Attribution licence (CC BY),
which permits reuse with attribution in the video description.
"""
import json
import random
import subprocess
import time
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import YOUTUBE_CLIENT_SECRETS_FILE, YOUTUBE_SCOPES, YOUTUBE_TOKEN_FILE
from utils.logger import get_logger

log = get_logger(__name__)

# Search queries for CC cricket Shorts
SEARCH_QUERIES = [
    "cricket highlights short",
    "cricket six wicket highlights",
    "cricket batting highlights short",
    "cricket match highlights",
    "cricket century highlights short",
]


def _get_youtube():
    """Build YouTube API client from saved OAuth token."""
    token_path = Path(YOUTUBE_TOKEN_FILE)
    if not token_path.exists():
        log.warning("YouTube token not found — cannot search for CC Shorts")
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


def _search_cc_shorts(youtube, query: str, max_results: int = 10) -> list[str]:
    """Return video IDs for CC-licensed Shorts matching the query."""
    try:
        resp = youtube.search().list(
            q=query,
            part="id",
            type="video",
            videoLicense="creativeCommon",   # CC BY licence only
            videoDuration="short",           # under 4 minutes (catches Shorts)
            order="viewCount",               # highest viewed first
            maxResults=max_results,
            relevanceLanguage="en",
            safeSearch="none",
        ).execute()
        ids = [item["id"]["videoId"] for item in resp.get("items", [])
               if item.get("id", {}).get("videoId")]
        log.info("Found %d CC Shorts for query '%s'", len(ids), query)
        return ids
    except Exception as exc:
        log.warning("CC Shorts search failed for '%s': %s", query, exc)
        return []


def _download_video(video_id: str, output_path: Path, timeout: int = 120) -> bool:
    """Download a YouTube video to output_path using yt-dlp. Returns True on success."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp",
        "--format", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "--output", str(output_path),
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 50_000:
            log.info("Downloaded CC Short %s -> %s (%.1f MB)",
                     video_id, output_path.name, output_path.stat().st_size / 1e6)
            return True
        log.warning("yt-dlp failed for %s: %s", video_id, result.stderr[-200:])
    except subprocess.TimeoutExpired:
        log.warning("yt-dlp timed out for %s", video_id)
    except FileNotFoundError:
        log.error("yt-dlp not found — install with: pip install yt-dlp")
    except Exception as exc:
        log.warning("Download error for %s: %s", video_id, exc)
    return False


def get_cc_cricket_short(output_path: Path, topic: str = "") -> Path | None:
    """
    Search YouTube for a CC-licensed cricket Short and download it.
    Returns the local video path on success, or None if not found.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    youtube = _get_youtube()
    if not youtube:
        log.warning("No YouTube client — skipping CC Shorts search")
        return None

    # Build a topic-specific query first, then fall back to generic ones
    queries = []
    if topic:
        queries.append(f"{topic} cricket highlights")
    queries.extend(random.sample(SEARCH_QUERIES, len(SEARCH_QUERIES)))

    tried_ids: set[str] = set()

    for query in queries[:3]:  # limit to 3 API calls to preserve quota
        video_ids = _search_cc_shorts(youtube, query, max_results=10)
        random.shuffle(video_ids)  # avoid always picking the same top result

        for video_id in video_ids:
            if video_id in tried_ids:
                continue
            tried_ids.add(video_id)

            candidate = output_path.with_suffix(".mp4")
            if _download_video(video_id, candidate):
                return candidate

            time.sleep(1)  # small delay between download attempts

    log.warning("Could not download any CC cricket Short")
    return None
