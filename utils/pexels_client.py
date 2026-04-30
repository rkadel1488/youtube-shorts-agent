"""Pexels free stock video search and download."""
import random
import time
from pathlib import Path

import requests

from config import PEXELS_API_KEY
from utils.logger import get_logger

log = get_logger(__name__)

PEXELS_VIDEO_SEARCH = "https://api.pexels.com/videos/search"
HEADERS = {"Authorization": PEXELS_API_KEY}


def search_videos(query: str, per_page: int = 10) -> list[dict]:
    """Return a list of Pexels video objects matching *query*."""
    try:
        resp = requests.get(
            PEXELS_VIDEO_SEARCH,
            headers=HEADERS,
            params={"query": query, "per_page": per_page, "orientation": "landscape"},
            timeout=15,
        )
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
        log.debug("Pexels: found %d videos for '%s'", len(videos), query)
        return videos
    except Exception as exc:
        log.warning("Pexels search failed for '%s': %s", query, exc)
        return []


def _best_file(video: dict, min_width: int = 1280) -> str | None:
    """Pick the highest-quality download URL that meets the minimum width."""
    files = sorted(
        video.get("video_files", []),
        key=lambda f: f.get("width", 0),
        reverse=True,
    )
    for f in files:
        if f.get("width", 0) >= min_width:
            return f.get("link")
    # Fall back to whatever exists
    return files[0]["link"] if files else None


def download_video(video: dict, dest_dir: Path, index: int) -> Path | None:
    """Download a single Pexels video to *dest_dir*. Returns the saved path."""
    url = _best_file(video)
    if not url:
        log.warning("No downloadable file found for video id=%s", video.get("id"))
        return None

    dest = dest_dir / f"clip_{index:02d}.mp4"
    try:
        log.info("Downloading clip %d from Pexels…", index)
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    f.write(chunk)
        log.info("Saved clip %d -> %s", index, dest)
        return dest
    except Exception as exc:
        log.warning("Failed to download clip %d: %s", index, exc)
        return None


def fetch_clips(keywords: list[str], count: int, dest_dir: Path) -> list[Path]:
    """
    Search Pexels with *keywords* and download *count* unique clips.
    Rotates through keywords if early queries don't return enough results.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    collected: list[Path] = []
    seen_ids: set[int] = set()

    for keyword in keywords:
        if len(collected) >= count:
            break
        videos = search_videos(keyword, per_page=15)
        random.shuffle(videos)
        for video in videos:
            if len(collected) >= count:
                break
            vid_id = video.get("id")
            if vid_id in seen_ids:
                continue
            seen_ids.add(vid_id)
            path = download_video(video, dest_dir, len(collected))
            if path:
                collected.append(path)
            time.sleep(0.3)  # polite rate-limiting

    log.info("Fetched %d/%d clips from Pexels", len(collected), count)
    return collected
