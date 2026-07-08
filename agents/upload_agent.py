"""
Uploads a video to YouTube via the YouTube Data API v3.

Credential-parameterized: pass the OAuth token JSON (dict) for the target
account directly, so multiple YouTube accounts can be uploaded to from one
process without one account's token leaking into another's request. A
thin CLI-compatible wrapper (upload_video_from_files) still reads the
config file paths for local/manual use.
"""
import json
import time
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from config import MADE_FOR_KIDS, YOUTUBE_SCOPES
from utils.logger import get_logger

log = get_logger(__name__)

UPLOAD_CHUNK_SIZE = 256 * 1024  # 256 KB
MAX_RETRIES = 5
RETRIABLE_STATUS_CODES = {500, 502, 503, 504}


def _credentials_from_token_info(token_info: dict) -> tuple[Credentials, dict]:
    """Build Credentials from an authorized-user token dict, refreshing if needed.

    Returns (creds, possibly_updated_token_info) so the caller can persist a
    refreshed token back to storage (e.g. the dashboard's encrypted DB row).
    """
    creds = Credentials.from_authorized_user_info(token_info, YOUTUBE_SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            log.info("Refreshing YouTube token...")
            creds.refresh(Request())
        else:
            raise RuntimeError(
                "YouTube token is invalid and has no refresh_token — "
                "re-run the OAuth setup for this account and paste a fresh token.")
    return creds, json.loads(creds.to_json())


def _build_body(
    title: str,
    description: str,
    tags: list[str],
    hashtags: list[str],
    category_id: str,
) -> dict:
    """Build the YouTube video metadata payload."""
    full_description = f"{description}\n\n{' '.join(hashtags)}"
    return {
        "snippet": {
            "title": title[:100],
            "description": full_description[:5000],
            "tags": tags[:500],
            "categoryId": category_id,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": MADE_FOR_KIDS,
        },
    }


def upload_video(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    hashtags: list[str],
    category_id: str,
    token_info: dict,
    retries: int = MAX_RETRIES,
) -> tuple[str, dict]:
    """
    Upload *video_path* to YouTube using the given account's token_info dict.
    Returns (video_id, refreshed_token_info) — persist refreshed_token_info
    if it differs from what was passed in (access tokens rotate).
    """
    creds, refreshed_token_info = _credentials_from_token_info(token_info)
    youtube = build("youtube", "v3", credentials=creds)

    body = _build_body(title, description, tags, hashtags, category_id)
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=UPLOAD_CHUNK_SIZE,
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    for attempt in range(1, retries + 1):
        try:
            log.info("Uploading '%s' (attempt %d)...", title, attempt)
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    log.info("Upload progress: %d%%", pct)

            video_id = response["id"]
            log.info("Upload complete! Video ID: %s", video_id)
            log.info("URL: https://www.youtube.com/shorts/%s", video_id)
            return video_id, refreshed_token_info

        except HttpError as exc:
            if exc.resp.status in RETRIABLE_STATUS_CODES:
                log.warning("Retriable HTTP %d on attempt %d", exc.resp.status, attempt)
                if attempt < retries:
                    time.sleep(2 ** attempt)
            else:
                raise
        except Exception as exc:
            log.warning("Upload error on attempt %d: %s", attempt, exc)
            if attempt < retries:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"Upload failed after {retries} attempts")


def upload_video_from_files(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    hashtags: list[str],
    category_id: str,
    token_file: str,
    retries: int = MAX_RETRIES,
) -> str:
    """CLI/local-use wrapper: reads token_file, uploads, writes back any refresh."""
    with open(token_file) as f:
        token_info = json.load(f)
    video_id, refreshed = upload_video(
        video_path, title, description, tags, hashtags, category_id,
        token_info, retries=retries)
    if refreshed != token_info:
        with open(token_file, "w") as f:
            json.dump(refreshed, f)
    return video_id
