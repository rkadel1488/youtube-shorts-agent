"""
Uploads a video to YouTube via the YouTube Data API v3.

Authentication uses OAuth 2.0. Run setup_youtube_auth.py once to create
the token file; this module refreshes it automatically on every run.
"""
import json
import time
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from config import (
    MADE_FOR_KIDS,
    YOUTUBE_CLIENT_SECRETS_FILE,
    YOUTUBE_SCOPES,
    YOUTUBE_TOKEN_FILE,
)
from utils.logger import get_logger

log = get_logger(__name__)

UPLOAD_CHUNK_SIZE = 256 * 1024  # 256 KB
MAX_RETRIES = 5
RETRIABLE_STATUS_CODES = {500, 502, 503, 504}


def _get_credentials() -> Credentials:
    """Load or refresh OAuth2 credentials. Opens browser on first run."""
    token_path = Path(YOUTUBE_TOKEN_FILE)
    creds = None

    if token_path.exists():
        with open(token_path) as f:
            creds = Credentials.from_authorized_user_info(json.load(f), YOUTUBE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing YouTube token…")
            creds.refresh(Request())
        else:
            log.info("Starting YouTube OAuth flow — browser will open…")
            flow = InstalledAppFlow.from_client_secrets_file(
                YOUTUBE_CLIENT_SECRETS_FILE, YOUTUBE_SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as f:
            f.write(creds.to_json())
        log.info("Token saved -> %s", token_path)

    return creds


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
    retries: int = MAX_RETRIES,
) -> str:
    """
    Upload *video_path* to YouTube with the supplied metadata.
    Returns the YouTube video ID on success.
    """
    creds = _get_credentials()
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

    video_id = None
    for attempt in range(1, retries + 1):
        try:
            log.info("Uploading '%s' (attempt %d)…", title, attempt)
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    log.info("Upload progress: %d%%", pct)

            video_id = response["id"]
            log.info("Upload complete! Video ID: %s", video_id)
            log.info("URL: https://www.youtube.com/shorts/%s", video_id)
            return video_id

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
