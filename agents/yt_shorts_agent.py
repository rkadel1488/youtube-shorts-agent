"""
Downloads a Creative Commons licensed cricket Short from YouTube using yt-dlp.

How it works:
  1. yt-dlp searches YouTube for cricket highlights
  2. Fetches metadata for the top results without downloading
  3. Filters for videos with a Creative Commons licence
  4. Downloads the first qualifying video as MP4

No YouTube API key needed — yt-dlp handles everything.
"""
import json
import subprocess
import time
from pathlib import Path

from utils.logger import get_logger

log = get_logger(__name__)

SEARCH_QUERIES = [
    "cricket highlights short creative commons",
    "cricket six wickets highlights creative commons",
    "cricket batting highlights creative commons",
    "cricket match highlights 2024 creative commons",
    "cricket best moments creative commons",
]


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


def download_cc_cricket_short(output_dir: Path) -> tuple[Path | None, dict]:
    """
    Find and download a CC-licensed cricket Short.
    Returns (video_path, video_info) on success, or (None, {}) on failure.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if not _ytdlp_available():
        log.error("yt-dlp is not installed. Run: pip install yt-dlp")
        return None, {}

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

    log.warning("No CC cricket Short found after searching all queries")
    return None, {}
