"""
Downloads a royalty-free sports/cricket background music track.

Sources used (all public domain / CC0 — safe for YouTube monetization):
  1. FreePD.com  — curated public domain sports tracks
  2. Internet Archive — CC0 uploads

Music plays at low volume behind the cricket highlight footage.
"""
import random
import time
from pathlib import Path

import requests

from utils.logger import get_logger

log = get_logger(__name__)

# Public domain sports / action tracks — no attribution required
MUSIC_TRACKS = [
    "https://freepd.com/music/Exciting%20Trailer.mp3",
    "https://freepd.com/music/Upbeat%20Forever.mp3",
    "https://freepd.com/music/Winning%20Elevation.mp3",
    "https://freepd.com/music/Power%20Sports.mp3",
    "https://freepd.com/music/Action%20News.mp3",
    "https://freepd.com/music/Sport%20Motivation.mp3",
    "https://freepd.com/music/Epic%20Cinematic%20Action.mp3",
    "https://freepd.com/music/Ambitious.mp3",
]


def download_music(output_path: Path, retries: int = 3) -> Path | None:
    """
    Download a random royalty-free music track to *output_path*.
    Returns the path on success, or None if all downloads fail.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tracks = random.sample(MUSIC_TRACKS, len(MUSIC_TRACKS))  # shuffle for variety

    for track_url in tracks:
        for attempt in range(1, retries + 1):
            try:
                log.info("Downloading music: %s (attempt %d)", track_url.split("/")[-1], attempt)
                resp = requests.get(
                    track_url,
                    timeout=30,
                    stream=True,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                if "audio" not in content_type and "mpeg" not in content_type and "octet" not in content_type:
                    raise ValueError(f"Not an audio response: {content_type}")

                with open(output_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        f.write(chunk)

                size_kb = output_path.stat().st_size // 1024
                if size_kb < 10:
                    raise ValueError(f"File too small ({size_kb} KB) — likely not audio")

                log.info("Music downloaded -> %s (%d KB)", output_path.name, size_kb)
                return output_path

            except Exception as exc:
                log.warning("Music download attempt %d failed: %s", attempt, exc)
                if output_path.exists():
                    output_path.unlink()
                if attempt < retries:
                    time.sleep(2 ** attempt)

    log.warning("All music downloads failed — video will have no background music")
    return None
