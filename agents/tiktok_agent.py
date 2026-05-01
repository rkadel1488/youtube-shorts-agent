"""
Uploads a video to TikTok via the Content Posting API v2.

Authentication uses OAuth 2.0. Run setup_tiktok_auth.py once to create
the token file; this module refreshes it automatically on every run.

TikTok API docs: https://developers.tiktok.com/doc/content-posting-api-get-started
"""
import json
import time
from pathlib import Path

import requests

from config import (
    TIKTOK_CLIENT_KEY,
    TIKTOK_CLIENT_SECRET,
    TIKTOK_TOKEN_FILE,
)
from utils.logger import get_logger

log = get_logger(__name__)

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

# Max caption length enforced by TikTok
CAPTION_MAX_LEN = 2200


def _load_token_data() -> dict:
    token_path = Path(TIKTOK_TOKEN_FILE)
    if not token_path.exists():
        raise RuntimeError(
            f"TikTok token file '{TIKTOK_TOKEN_FILE}' not found. "
            "Run setup_tiktok_auth.py first."
        )
    with open(token_path) as f:
        return json.load(f)


def _save_token_data(data: dict):
    with open(TIKTOK_TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _refresh_access_token(refresh_token: str) -> dict:
    """Exchange a refresh_token for a new access_token."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_key": TIKTOK_CLIENT_KEY,
            "client_secret": TIKTOK_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _get_access_token() -> str:
    """Return a valid access token, refreshing if necessary."""
    data = _load_token_data()

    expires_at = data.get("expires_at", 0)
    if time.time() < expires_at - 300:  # 5-minute safety buffer
        return data["access_token"]

    log.info("TikTok access token expired — refreshing…")
    refreshed = _refresh_access_token(data["refresh_token"])
    refreshed["expires_at"] = time.time() + refreshed.get("expires_in", 86400)
    _save_token_data(refreshed)
    log.info("TikTok token refreshed.")
    return refreshed["access_token"]


def upload_to_tiktok(
    video_path: Path,
    title: str,
    hashtags: list[str],
    retries: int = 3,
) -> str:
    """
    Upload *video_path* to TikTok as a public post.
    Returns the publish_id on success.
    """
    access_token = _get_access_token()
    caption = f"{title}\n\n{' '.join(hashtags)}"[:CAPTION_MAX_LEN]
    video_size = video_path.stat().st_size

    api_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }

    for attempt in range(1, retries + 1):
        try:
            # ── Step 1: Initialise upload ─────────────────────────────────────
            log.info("Initialising TikTok upload (attempt %d)…", attempt)
            init_payload = {
                "post_info": {
                    "title": caption,
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                    "video_cover_timestamp_ms": 1000,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": video_size,
                    "chunk_size": video_size,
                    "total_chunk_count": 1,
                },
            }

            resp = requests.post(INIT_URL, headers=api_headers, json=init_payload, timeout=30)
            resp.raise_for_status()
            init_data = resp.json()

            err = init_data.get("error", {})
            if err.get("code", "ok") != "ok":
                raise RuntimeError(f"TikTok init error: {err}")

            upload_url = init_data["data"]["upload_url"]
            publish_id = init_data["data"]["publish_id"]
            log.info("TikTok upload initialised. publish_id: %s", publish_id)

            # ── Step 2: Upload video bytes ────────────────────────────────────
            with open(video_path, "rb") as f:
                video_bytes = f.read()

            upload_headers = {
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
                "Content-Length": str(video_size),
            }
            put_resp = requests.put(
                upload_url, headers=upload_headers, data=video_bytes, timeout=300
            )
            put_resp.raise_for_status()
            log.info("TikTok video bytes uploaded — waiting for processing…")

            # ── Step 3: Poll publish status ───────────────────────────────────
            for poll in range(12):
                time.sleep(5)
                status_resp = requests.post(
                    STATUS_URL,
                    headers=api_headers,
                    json={"publish_id": publish_id},
                    timeout=30,
                )
                status_data = status_resp.json()
                status = status_data.get("data", {}).get("status", "PROCESSING")
                log.info("TikTok publish status (poll %d): %s", poll + 1, status)

                if status == "PUBLISH_COMPLETE":
                    log.info("TikTok upload complete! publish_id: %s", publish_id)
                    return publish_id
                if status in ("FAILED", "CANCELLED"):
                    raise RuntimeError(f"TikTok publish failed: {status_data}")

            raise RuntimeError("TikTok publish timed out after polling")

        except Exception as exc:
            log.warning("TikTok upload attempt %d failed: %s", attempt, exc)
            if attempt < retries:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"TikTok upload failed after {retries} attempts")
