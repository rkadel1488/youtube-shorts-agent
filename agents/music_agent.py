"""
Downloads a royalty-free track from the YouTube Audio Library.

YouTube Audio Library tracks are 100% free to use on YouTube with no
copyright claims, even on monetized videos.

Strategy:
  1. Pick a random track ID from a curated list of YouTube Audio Library
     sports / action tracks (these are the actual YouTube video IDs for
     each track as listed in the public audio library).
  2. Download the audio using yt-dlp and convert to MP3.
  3. Fall back to FreePD.com public domain tracks if yt-dlp fails.
"""
import random
import subprocess
import time
from pathlib import Path

import requests

from utils.logger import get_logger

log = get_logger(__name__)

# ── YouTube Audio Library — sports/action tracks ──────────────────────────
# These are official YouTube Audio Library track IDs (video IDs on YouTube).
# All are free to use on YouTube, no attribution required.
YT_AUDIO_LIBRARY_TRACKS = [
    # Sports & Action genre — no attribution required
    "https://www.youtube.com/watch?v=ckxMQeOa_Yo",   # Faster Does It
    "https://www.youtube.com/watch?v=R8GfV5Z7OLY",   # Rollin At 5
    "https://www.youtube.com/watch?v=0OIXF2RkVdA",   # MBB - Wake up
    "https://www.youtube.com/watch?v=Y_l3ButeDk0",   # Impact Moderato
    "https://www.youtube.com/watch?v=EzGxFbUnAW0",   # Powerful Trap
    "https://www.youtube.com/watch?v=Q2oMBq3vvIk",   # Hotshot
    "https://www.youtube.com/watch?v=TGTWXejA9HE",   # Run Amok
    "https://www.youtube.com/watch?v=q_5bXkAmv8A",   # Cut and Run
    "https://www.youtube.com/watch?v=qRUefh2YQUA",   # Upbeat Forever
    "https://www.youtube.com/watch?v=bhxTKDgPZhw",   # Savage
]

# ── FreePD.com fallback — true public domain ──────────────────────────────
FREEPD_TRACKS = [
    "https://freepd.com/music/Exciting%20Trailer.mp3",
    "https://freepd.com/music/Winning%20Elevation.mp3",
    "https://freepd.com/music/Action%20News.mp3",
    "https://freepd.com/music/Ambitious.mp3",
    "https://freepd.com/music/Upbeat%20Forever.mp3",
]


def _download_yt_audio(track_url: str, output_path: Path, timeout: int = 90) -> bool:
    """Download audio from a YouTube Audio Library URL using yt-dlp."""
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "128K",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "--output", str(output_path.with_suffix("")),   # yt-dlp appends .mp3
        track_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        # yt-dlp may name it slightly differently — find the mp3
        mp3_candidates = list(output_path.parent.glob(output_path.stem + "*.mp3"))
        if mp3_candidates:
            mp3_candidates[0].rename(output_path)
        if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 10_000:
            log.info("YouTube Audio Library track downloaded -> %s (%.0f KB)",
                     output_path.name, output_path.stat().st_size / 1024)
            return True
        log.warning("yt-dlp audio failed: %s", result.stderr[-200:])
    except subprocess.TimeoutExpired:
        log.warning("yt-dlp audio download timed out")
    except FileNotFoundError:
        log.warning("yt-dlp not found")
    except Exception as exc:
        log.warning("Audio download error: %s", exc)
    return False


def _download_freepd(output_path: Path) -> bool:
    """Download a random FreePD.com public domain track as fallback."""
    tracks = random.sample(FREEPD_TRACKS, len(FREEPD_TRACKS))
    for url in tracks:
        try:
            resp = requests.get(url, timeout=30, stream=True,
                                headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(65536):
                    f.write(chunk)
            if output_path.stat().st_size > 10_000:
                log.info("FreePD fallback track downloaded -> %s", output_path.name)
                return True
        except Exception as exc:
            log.warning("FreePD download failed: %s", exc)
            if output_path.exists():
                output_path.unlink()
    return False


def download_music(output_path: Path) -> Path | None:
    """
    Download a YouTube Audio Library sports track (or FreePD fallback).
    Returns the MP3 path on success, or None if everything fails.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try YouTube Audio Library tracks first (best for YouTube — no claims)
    tracks = random.sample(YT_AUDIO_LIBRARY_TRACKS, len(YT_AUDIO_LIBRARY_TRACKS))
    for track_url in tracks[:4]:   # try up to 4 before falling back
        if _download_yt_audio(track_url, output_path):
            return output_path
        time.sleep(1)

    # Fallback: FreePD public domain
    log.info("Falling back to FreePD.com for background music...")
    if _download_freepd(output_path):
        return output_path

    log.warning("All music downloads failed — video will be silent")
    return None
