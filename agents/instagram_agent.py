"""
Cross-posts the rendered video to Instagram Reels via the Instagram Graph API.

Instagram cannot accept file uploads — it downloads the video from a public
URL. This agent temporarily hosts the video as a GitHub release asset (using
the Actions-provided GH_TOKEN), tells Instagram to fetch it, waits for
processing, publishes, then deletes the release.

Required env / secrets:
  IG_USER_ID       — Instagram professional account's IG User ID (numeric)
  IG_ACCESS_TOKEN  — long-lived Instagram Graph API access token
  GH_TOKEN         — GitHub token with contents:write (Actions provides this)
  GITHUB_REPOSITORY — owner/repo (auto-set by GitHub Actions)

If IG secrets are missing, post_reel() raises with a clear message; the
caller treats Instagram as optional/non-fatal.
"""
import os
import time
from pathlib import Path

import requests

from utils.logger import get_logger

log = get_logger(__name__)

GRAPH = "https://graph.facebook.com/v21.0"
GH_API = "https://api.github.com"

IG_USER_ID = os.getenv("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
GH_TOKEN = os.getenv("GH_TOKEN", "")
GH_REPO = os.getenv("GITHUB_REPOSITORY", "")


# ── temporary public hosting via GitHub release asset ─────────────────────────

def _gh_headers() -> dict:
    return {"Authorization": f"token {GH_TOKEN}",
            "Accept": "application/vnd.github+json"}


def _host_on_github(video_path: Path, tag: str) -> tuple[str, int]:
    """Create a prerelease with the video as asset; return (public_url, release_id)."""
    r = requests.post(
        f"{GH_API}/repos/{GH_REPO}/releases",
        headers=_gh_headers(),
        json={"tag_name": tag, "name": f"temp reel host {tag}",
              "prerelease": True,
              "body": "Temporary hosting for Instagram Reels publish — auto-deleted."},
        timeout=30,
    )
    r.raise_for_status()
    release = r.json()
    upload_url = release["upload_url"].split("{")[0]

    with open(video_path, "rb") as f:
        r = requests.post(
            f"{upload_url}?name=reel.mp4",
            headers={**_gh_headers(), "Content-Type": "video/mp4"},
            data=f.read(),
            timeout=300,
        )
    r.raise_for_status()
    url = r.json()["browser_download_url"]
    log.info("Video temporarily hosted: %s", url)
    return url, release["id"]


def _cleanup_github(release_id: int, tag: str) -> None:
    try:
        requests.delete(f"{GH_API}/repos/{GH_REPO}/releases/{release_id}",
                        headers=_gh_headers(), timeout=30)
        requests.delete(f"{GH_API}/repos/{GH_REPO}/git/refs/tags/{tag}",
                        headers=_gh_headers(), timeout=30)
        log.info("Temporary release cleaned up")
    except Exception as exc:  # cleanup best-effort
        log.warning("Release cleanup failed (harmless): %s", exc)


# ── Instagram Graph API publish flow ──────────────────────────────────────────

def _create_container(video_url: str, caption: str) -> str:
    r = requests.post(
        f"{GRAPH}/{IG_USER_ID}/media",
        data={"media_type": "REELS", "video_url": video_url,
              "caption": caption[:2200], "share_to_feed": "true",
              "access_token": IG_ACCESS_TOKEN},
        timeout=60,
    )
    data = r.json()
    if "id" not in data:
        raise RuntimeError(f"IG container creation failed: {data.get('error', data)}")
    return data["id"]


def _wait_until_ready(container_id: str, timeout_s: int = 300) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = requests.get(
            f"{GRAPH}/{container_id}",
            params={"fields": "status_code,status", "access_token": IG_ACCESS_TOKEN},
            timeout=30,
        )
        data = r.json()
        code = data.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"IG processing error: {data.get('status')}")
        log.info("IG processing... (%s)", code)
        time.sleep(10)
    raise RuntimeError("IG processing timed out")


def _publish(container_id: str) -> str:
    r = requests.post(
        f"{GRAPH}/{IG_USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": IG_ACCESS_TOKEN},
        timeout=60,
    )
    data = r.json()
    if "id" not in data:
        raise RuntimeError(f"IG publish failed: {data.get('error', data)}")
    return data["id"]


def post_reel(video_path: Path, caption: str) -> str:
    """Full flow: host video publicly → create container → wait → publish → cleanup.

    Returns the Instagram media ID.
    """
    if not (IG_USER_ID and IG_ACCESS_TOKEN):
        raise RuntimeError("Instagram not configured (IG_USER_ID / IG_ACCESS_TOKEN secrets missing)")
    if not (GH_TOKEN and GH_REPO):
        raise RuntimeError("GH_TOKEN / GITHUB_REPOSITORY missing — cannot host video for Instagram")

    tag = f"reel-temp-{int(time.time())}"
    video_url, release_id = _host_on_github(Path(video_path), tag)
    try:
        log.info("Creating IG media container...")
        container = _create_container(video_url, caption)
        _wait_until_ready(container)
        media_id = _publish(container)
        log.info("Instagram Reel published: media id %s", media_id)
        return media_id
    finally:
        _cleanup_github(release_id, tag)
