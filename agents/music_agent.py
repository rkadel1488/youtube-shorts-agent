"""
Downloads a free sports/action music track using yt-dlp.

Sources tried in order:
  1. NoCopyrightSounds (NCS) — explicitly free to use on YouTube, no claims
  2. FreePD.com direct MP3 — 100% public domain, no attribution needed

NCS tracks are specifically approved for YouTube use (monetized or not).
"""
import random
import subprocess
import time
from pathlib import Path

import requests

from utils.logger import get_logger

log = get_logger(__name__)

# NCS and similar channels that explicitly allow YouTube use (no Content ID claims)
# These are real YouTube video IDs of sports/action tracks
NCS_TRACK_URLS = [
    "https://www.youtube.com/watch?v=BnTCMpAAWPE",  # NCS: Elektronomia - Sky High
    "https://www.youtube.com/watch?v=TW9d8vYrVFQ",  # NCS: Jim Yosef - Speed
    "https://www.youtube.com/watch?v=QL_6VApDxmc",  # NCS: Cartoon - On & On
    "https://www.youtube.com/watch?v=gQjAEbWZFo4",  # NCS: Warriyo - Mortals
    "https://www.youtube.com/watch?v=VjL-w0YWGAI",  # NCS: DEAF KEV - Invincible
    "https://www.youtube.com/watch?v=h7ArUgxtlJs",  # NCS: Distrion & Alex Skrindo - Lightning
    "https://www.youtube.com/watch?v=2Nv5juZKhKo",  # NCS: Electro-Light - Symbolism
    "https://www.youtube.com/watch?v=yJg-Y5byMMw",  # NCS: Vanze - Forever
]

# FreePD fallback — true public domain
FREEPD_TRACKS = [
    "https://freepd.com/music/Exciting%20Trailer.mp3",
    "https://freepd.com/music/Action%20News.mp3",
    "https://freepd.com/music/Ambitious.mp3",
]


def _download_yt_audio(url: str, output_path: Path) -> bool:
    """Download audio from a YouTube URL as MP3 via yt-dlp."""
    # yt-dlp adds extension automatically; we point to stem
    out_template = str(output_path.with_suffix("")) + ".%(ext)s"
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "128K",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "--output", out_template,
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        # Find the resulting mp3 (yt-dlp may name it with the video title)
        mp3_files = sorted(output_path.parent.glob("*.mp3"))
        if mp3_files and mp3_files[-1].stat().st_size > 10_000:
            mp3_files[-1].rename(output_path)
            log.info("Music downloaded -> %s (%.0f KB)",
                     output_path.name, output_path.stat().st_size / 1024)
            return True
        log.warning("yt-dlp audio failed: %s", result.stderr[-200:])
    except subprocess.TimeoutExpired:
        log.warning("Music download timed out")
    except FileNotFoundError:
        log.warning("yt-dlp not installed")
    except Exception as exc:
        log.warning("Music download error: %s", exc)
    return False


def _download_freepd(output_path: Path) -> bool:
    """Download a FreePD public domain track as final fallback."""
    for url in random.sample(FREEPD_TRACKS, len(FREEPD_TRACKS)):
        try:
            resp = requests.get(url, timeout=30, stream=True,
                                headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(65536):
                    f.write(chunk)
            if output_path.stat().st_size > 10_000:
                log.info("FreePD track downloaded -> %s", output_path.name)
                return True
        except Exception as exc:
            log.warning("FreePD download failed: %s", exc)
            if output_path.exists():
                output_path.unlink()
    return False


def download_music(output_path: Path) -> Path | None:
    """
    Download a free sports music track.
    Tries NCS YouTube tracks first, then FreePD fallback.
    Returns the MP3 path on success, or None.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for url in random.sample(NCS_TRACK_URLS, min(4, len(NCS_TRACK_URLS))):
        log.info("Trying NCS track: %s", url)
        if _download_yt_audio(url, output_path):
            return output_path
        time.sleep(1)

    log.info("NCS downloads failed — trying FreePD fallback...")
    if _download_freepd(output_path):
        return output_path

    log.warning("All music downloads failed")
    return None
