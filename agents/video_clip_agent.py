"""
Fetches copyright-free stock video clips from Pexels Video API.
Returns downloaded MP4 paths for use in video composition.
"""
import random
import time
from pathlib import Path

import requests

from config import PEXELS_API_KEY
from utils.logger import get_logger

log = get_logger(__name__)

PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"


def _best_mp4(video: dict) -> str | None:
    """Return the URL of the best available MP4 file for a Pexels video."""
    files = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4"]
    if not files:
        return None
    # Prefer HD (720p+) but accept anything
    files.sort(key=lambda f: f.get("height", 0), reverse=True)
    return files[0]["link"]


def fetch_clips(
    keywords: list[str],
    output_dir: Path,
    num_clips: int = 5,
    retries: int = 3,
) -> list[Path]:
    """
    Search Pexels for portrait video clips matching keywords and download them.
    Returns a list of saved MP4 paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for keyword in keywords:
        if len(paths) >= num_clips:
            break
        for attempt in range(1, retries + 1):
            try:
                page = random.randint(1, 8)
                resp = requests.get(
                    PEXELS_VIDEO_URL,
                    headers={"Authorization": PEXELS_API_KEY},
                    params={
                        "query": keyword,
                        "per_page": 15,
                        "page": page,
                        "orientation": "portrait",
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                videos = resp.json().get("videos", [])
                random.shuffle(videos)

                for video in videos:
                    if len(paths) >= num_clips:
                        break
                    url = _best_mp4(video)
                    if not url:
                        continue
                    clip_path = output_dir / f"clip_{len(paths):02d}.mp4"
                    dl = requests.get(url, timeout=90, stream=True)
                    dl.raise_for_status()
                    with open(clip_path, "wb") as f:
                        for chunk in dl.iter_content(chunk_size=65536):
                            f.write(chunk)
                    log.info("Downloaded clip %d from Pexels (%s)", len(paths) + 1, keyword)
                    paths.append(clip_path)

                break  # keyword search succeeded — move on

            except Exception as exc:
                log.warning("Pexels fetch attempt %d failed for '%s': %s", attempt, keyword, exc)
                if attempt < retries:
                    time.sleep(2 ** attempt)

    # Fallback: if still short, retry with generic terms
    fallbacks = ["nature", "city", "abstract", "sky", "water"]
    for kw in fallbacks:
        if len(paths) >= num_clips:
            break
        try:
            resp = requests.get(
                PEXELS_VIDEO_URL,
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": kw, "per_page": 10, "page": 1, "orientation": "portrait"},
                timeout=30,
            )
            resp.raise_for_status()
            for video in resp.json().get("videos", []):
                if len(paths) >= num_clips:
                    break
                url = _best_mp4(video)
                if not url:
                    continue
                clip_path = output_dir / f"clip_{len(paths):02d}.mp4"
                dl = requests.get(url, timeout=90, stream=True)
                dl.raise_for_status()
                with open(clip_path, "wb") as f:
                    for chunk in dl.iter_content(chunk_size=65536):
                        f.write(chunk)
                paths.append(clip_path)
        except Exception as exc:
            log.warning("Fallback clip fetch failed for '%s': %s", kw, exc)

    log.info("Fetched %d/%d clips total", len(paths), num_clips)
    return paths
