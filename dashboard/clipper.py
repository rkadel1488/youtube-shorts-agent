"""
Turns an existing YouTube video into a vertical Short: downloads it,
pulls the transcript, has Claude pick the single most compelling
30-60s window (with a hook title), then cuts + reframes to 9:16.

Requires the source video to have captions (manual or auto-generated) —
this is true for the vast majority of YouTube videos. If none exist, the
function raises a clear error rather than guessing at content via
guesswork transcription (no ASR model is bundled).
"""
import json
import os
import re
import subprocess
from pathlib import Path

import anthropic
from imageio_ffmpeg import get_ffmpeg_exe
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from utils.logger import get_logger

log = get_logger(__name__)

# YouTube frequently blocks download requests from datacenter/VPS IPs with
# "Sign in to confirm you're not a bot." Passing cookies from a real,
# logged-in browser session works around this. Set YTDLP_COOKIES to the
# full contents of a Netscape-format cookies.txt (exported via a browser
# extension like "Get cookies.txt LOCALLY"), and it's written to a temp
# file here for yt-dlp to use. Optional — downloads without it may still
# work for some videos, and will raise a clear error when they don't.
_COOKIES_PATH = None
if os.getenv("YTDLP_COOKIES", "").strip():
    _COOKIES_PATH = Path("/tmp/ytdlp_cookies.txt")
    _COOKIES_PATH.write_text(os.environ["YTDLP_COOKIES"])
    log.info("yt-dlp cookies configured (%d bytes)", _COOKIES_PATH.stat().st_size)

CLIP_SYSTEM_PROMPT = """You select the single most compelling 30-60 second segment from a
video transcript for repurposing as a vertical Short. You pick the moment with the strongest
hook, biggest payoff, or most surprising claim — not just the first interesting bit.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

CLIP_TEMPLATE = """Here is a timestamped transcript of a YouTube video:

{transcript}

Pick the SINGLE best 30-60 second window to repurpose as a standalone vertical Short.
Rules:
- The window must make sense on its own, without earlier context from the video
- Prefer segments with a strong claim, a surprising fact, a punchline, or emotional peak
- start_seconds and end_seconds must be actual timestamps present in the transcript
- Keep the window between 30 and 60 seconds

Return ONLY this JSON:
{{
  "start_seconds": 0,
  "end_seconds": 0,
  "hook_title": "short catchy title for this clip, max 8 words",
  "reason": "one sentence on why this moment was chosen"
}}"""


def _extract_video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
    if not m:
        raise ValueError(f"Could not extract a video ID from URL: {url}")
    return m.group(1)


def _transcript_api_client() -> YouTubeTranscriptApi:
    """Build the transcript client, optionally routed through a Webshare
    residential proxy — youtube-transcript-api's own recommended fix for
    RequestBlocked/IpBlocked errors on datacenter/VPS IPs (the library
    explicitly advises AGAINST a cookie-based workaround here, unlike
    yt-dlp's download step, since it risks permanently banning the Google
    account used). Optional: set WEBSHARE_PROXY_USERNAME/PASSWORD to
    enable; without them, requests go out directly as before.
    """
    username = os.getenv("WEBSHARE_PROXY_USERNAME", "")
    password = os.getenv("WEBSHARE_PROXY_PASSWORD", "")
    if username and password:
        from youtube_transcript_api.proxies import WebshareProxyConfig
        return YouTubeTranscriptApi(proxy_config=WebshareProxyConfig(
            proxy_username=username, proxy_password=password))
    return YouTubeTranscriptApi()


def fetch_transcript(video_id: str) -> list[dict]:
    """[{"text":..., "start":..., "duration":...}, ...]. Raises if no captions exist.

    Uses the instance-based API (youtube-transcript-api >= 1.0) — the old
    static YouTubeTranscriptApi.get_transcript() was removed in v1.2.0.
    """
    try:
        ytt_api = _transcript_api_client()
        fetched = ytt_api.fetch(video_id)
        return fetched.to_raw_data()  # same [{"text","start","duration"}, ...] shape as before
    except Exception as exc:
        exc_name = exc.__class__.__name__
        exc_chain = f"{exc_name}: {exc}"
        # Any of these indicate YouTube is throttling/blocking this IP, NOT that
        # the video lacks captions — catching the specific RequestBlocked/
        # IpBlocked types alone missed raw 429s surfacing as urllib3/requests
        # retry errors instead.
        is_rate_limited_or_blocked = (
            "Blocked" in exc_name
            or "429" in exc_chain
            or "RetryError" in exc_chain
            or "MaxRetryError" in exc_chain
            or "TooManyRequests" in exc_chain
        )
        if is_rate_limited_or_blocked:
            raise RuntimeError(
                f"YouTube is rate-limiting/blocking transcript requests from this "
                f"server's IP ({exc_name}). This is a known issue for cloud/VPS IP "
                "ranges — it's not about this specific video, and retrying the same "
                "video repeatedly in a short window can make it worse. Set "
                "WEBSHARE_PROXY_USERNAME/PASSWORD (see dashboard/README.md) to route "
                "around it — this is the library's own recommended fix; a cookie-based "
                "workaround is deliberately not used here since it risks getting the "
                "authenticating Google account banned.")
        raise RuntimeError(
            f"No transcript/captions available for this video ({exc_name}: {exc}). "
            "The clipper needs existing captions (manual or auto-generated) "
            "to pick a moment — it does not run its own speech recognition.")


def _format_transcript(entries: list[dict]) -> str:
    lines = []
    for e in entries:
        start = int(e["start"])
        lines.append(f"[{start//60}:{start%60:02d}] {e['text']}")
    return "\n".join(lines)


def pick_best_clip(transcript_entries: list[dict], retries: int = 3) -> dict:
    transcript_text = _format_transcript(transcript_entries)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    last_ts = transcript_entries[-1]["start"] + transcript_entries[-1].get("duration", 0)

    for attempt in range(1, retries + 1):
        try:
            message = client.messages.create(
                model=CLAUDE_MODEL, max_tokens=512,
                system=CLIP_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": CLIP_TEMPLATE.format(transcript=transcript_text)}],
            )
            result = json.loads(message.content[0].text.strip())
            start, end = float(result["start_seconds"]), float(result["end_seconds"])
            if not (0 <= start < end <= last_ts + 5) or not (20 <= end - start <= 90):
                raise ValueError(f"Implausible window: {start}-{end} (video length ~{last_ts:.0f}s)")
            return result
        except Exception as exc:
            log.warning("Clip selection attempt %d failed: %s", attempt, exc)
    raise RuntimeError(f"Could not pick a valid clip window after {retries} attempts")


def download_video(url: str, out_path: Path) -> Path:
    ydl_opts = {
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(out_path),
        "quiet": True,
        "merge_output_format": "mp4",
    }
    if _COOKIES_PATH:
        ydl_opts["cookiefile"] = str(_COOKIES_PATH)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as exc:
        if "Sign in to confirm" in str(exc) and not _COOKIES_PATH:
            raise RuntimeError(
                "YouTube is blocking this download as bot traffic (common for "
                "server/VPS IPs). Fix: export cookies.txt from a logged-in "
                "browser (e.g. the 'Get cookies.txt LOCALLY' extension) and "
                "set it as the YTDLP_COOKIES environment variable — see "
                "dashboard/README.md.") from exc
        raise

    if not out_path.exists():
        candidates = list(out_path.parent.glob(out_path.stem + "*"))
        if not candidates:
            raise RuntimeError("yt-dlp reported success but no output file was found")
        return candidates[0]
    return out_path


def cut_and_reframe(source_path: Path, start: float, end: float, out_path: Path,
                    width: int = 1080, height: int = 1920) -> Path:
    """Cut [start,end] and reframe to vertical: center-crop if source is wide,
    blurred-background pillarbox if source is already narrower than target ratio."""
    ffmpeg = get_ffmpeg_exe()
    duration = end - start
    vf = (
        f"crop='min(iw,ih*{width}/{height})':'min(ih,iw*{height}/{width})',"
        f"scale={width}:{height}"
    )
    subprocess.run(
        [ffmpeg, "-y", "-ss", f"{start:.2f}", "-i", str(source_path), "-t", f"{duration:.2f}",
         "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out_path)],
        capture_output=True, check=True,
    )
    return out_path


def clip_youtube_video(youtube_url: str, work_dir: Path) -> dict:
    """Full flow: download -> transcript -> pick moment -> cut/reframe.

    Returns {"video_path": Path, "hook_title": str, "reason": str,
             "start_seconds": float, "end_seconds": float}.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    video_id = _extract_video_id(youtube_url)

    log.info("Fetching transcript for %s...", video_id)
    transcript = fetch_transcript(video_id)

    log.info("Selecting best clip window via Claude...")
    choice = pick_best_clip(transcript)
    log.info("Selected %.0fs-%.0fs: %s", choice["start_seconds"], choice["end_seconds"], choice["hook_title"])

    log.info("Downloading source video...")
    source_path = download_video(youtube_url, work_dir / "source.mp4")

    log.info("Cutting and reframing to vertical...")
    clip_path = cut_and_reframe(source_path, choice["start_seconds"], choice["end_seconds"],
                                work_dir / "clip.mp4")

    return {
        "video_path": clip_path,
        "hook_title": choice["hook_title"],
        "reason": choice.get("reason", ""),
        "start_seconds": choice["start_seconds"],
        "end_seconds": choice["end_seconds"],
    }
