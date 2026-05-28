"""
Downloads a Creative Commons licensed cricket Short from YouTube using yt-dlp.
Falls back to Pexels stock cricket footage if no CC Short is found.

How it works:
  1. yt-dlp searches YouTube for cricket highlights
  2. Fetches metadata for the top results without downloading
  3. Filters for videos with a Creative Commons licence
  4. Downloads the first qualifying video as MP4
  5. If nothing found, tries Pexels free stock cricket videos

No YouTube API key needed for the CC search — yt-dlp handles everything.
"""
import json
import subprocess
import time
from pathlib import Path

import requests

from config import PEXELS_API_KEY
from utils.logger import get_logger

log = get_logger(__name__)

SEARCH_QUERIES = [
    "cricket highlights short creative commons",
    "cricket six wickets highlights creative commons",
    "cricket batting highlights creative commons",
    "cricket match highlights 2024 creative commons",
    "cricket best moments creative commons",
]

PEXELS_QUERIES = ["cricket sport", "cricket match", "cricket ball", "cricket player"]


def _ytdlp_available() -> bool:
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _fetch_metadata(query: str, count: int = 25) -> list[dict]:
    """Return metadata dicts for the top *count* search results (no download)."""
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
    except subprocess.TimeoutExpired:
        log.warning("Metadata fetch timed out for query: %s", query)
    except Exception as exc:
        log.warning("Metadata fetch error: %s", exc)
    return []


def _is_cc_licensed(video: dict) -> bool:
    """Return True if the video carries a Creative Commons licence."""
    license_field = (video.get("license") or "").lower()
    return "creative commons" in license_field


def _download_video(video_id: str, output_path: Path, timeout: int = 180) -> bool:
    """Download a single YouTube video as MP4. Returns True on success."""
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
        if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 100_000:
            log.info("Downloaded CC Short '%s' -> %s (%.1f MB)",
                     video_id, output_path.name, output_path.stat().st_size / 1e6)
            return True
        log.warning("Download failed for %s: %s", video_id, result.stderr[-300:])
    except subprocess.TimeoutExpired:
        log.warning("Download timed out for %s", video_id)
    except Exception as exc:
        log.warning("Download error for %s: %s", video_id, exc)
    if output_path.exists():
        output_path.unlink()
    return False


def _download_pexels_fallback(output_dir: Path) -> tuple[Path | None, dict]:
    """Download a free cricket stock video from Pexels API as last-resort fallback."""
    if not PEXELS_API_KEY:
        log.warning("PEXELS_API_KEY not set — cannot use Pexels fallback")
        return None, {}

    for query in PEXELS_QUERIES:
        try:
            resp = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": query, "per_page": 15, "size": "medium"},
                timeout=30,
            )
            resp.raise_for_status()
            videos = resp.json().get("videos", [])

            for video in videos:
                duration = video.get("duration", 0) or 0
                if duration < 5 or duration > 180:
                    continue

                # Pick the largest file that isn't too big to download quickly
                video_files = sorted(
                    video.get("video_files", []),
                    key=lambda f: f.get("width", 0) * f.get("height", 0),
                    reverse=True,
                )
                for vf in video_files:
                    link = vf.get("link")
                    if not link:
                        continue
                    # Skip if resolution too high (takes too long)
                    if max(vf.get("width", 0), vf.get("height", 0)) > 1920:
                        continue

                    out_path = output_dir / f"pexels_{video['id']}.mp4"
                    try:
                        r2 = requests.get(
                            link, timeout=120, stream=True,
                            headers={"User-Agent": "Mozilla/5.0"},
                        )
                        r2.raise_for_status()
                        with open(out_path, "wb") as f:
                            for chunk in r2.iter_content(65536):
                                f.write(chunk)
                        if out_path.exists() and out_path.stat().st_size > 100_000:
                            info = {
                                "title":      "Cricket Highlights",
                                "channel":    video.get("user", {}).get("name", "Pexels"),
                                "video_id":   str(video["id"]),
                                "duration":   duration,
                                "view_count": 0,
                                "license":    "Pexels License (free to use)",
                            }
                            log.info("Pexels fallback downloaded -> %s (%.1f MB)",
                                     out_path.name, out_path.stat().st_size / 1e6)
                            return out_path, info
                    except Exception as exc:
                        log.warning("Pexels video download error: %s", exc)
                        if out_path.exists():
                            out_path.unlink()
                    break  # tried the best file for this video, move on
        except Exception as exc:
            log.warning("Pexels search failed for '%s': %s", query, exc)

    log.warning("Pexels fallback also found nothing")
    return None, {}


def download_cc_cricket_short(output_dir: Path) -> tuple[Path | None, dict]:
    """
    Find and download a CC-licensed cricket Short.
    Falls back to Pexels stock footage if no CC Short is found.
    Returns (video_path, video_info) on success, or (None, {}) on failure.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if not _ytdlp_available():
        log.error("yt-dlp is not installed. Run: pip install yt-dlp")
        log.info("Trying Pexels fallback instead...")
        return _download_pexels_fallback(output_dir)

    for query in SEARCH_QUERIES:
        log.info("Searching YouTube: '%s'", query)
        videos = _fetch_metadata(query, count=25)

        cc_videos = [v for v in videos if _is_cc_licensed(v)]
        log.info("Found %d CC-licensed results for '%s'", len(cc_videos), query)

        for video in cc_videos:
            video_id = video.get("id") or video.get("webpage_url_basename", "")
            if not video_id:
                continue
            duration = video.get("duration", 0) or 0
            # Only use videos under 3 minutes (proper Shorts / short clips)
            if duration > 180:
                continue

            out_path = output_dir / f"{video_id}.mp4"
            if _download_video(video_id, out_path):
                info = {
                    "title":       video.get("title", "Cricket Highlights"),
                    "channel":     video.get("uploader", ""),
                    "video_id":    video_id,
                    "duration":    duration,
                    "view_count":  video.get("view_count", 0),
                    "license":     video.get("license", ""),
                }
                return out_path, info

        time.sleep(2)

    log.warning("No CC cricket Short found — trying Pexels stock footage fallback...")
    return _download_pexels_fallback(output_dir)
