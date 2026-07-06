"""
Cross-posts the rendered video to Instagram Reels and the Facebook Page
via the Meta Graph API.

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

PAGE_ID = ""
PAGE_TOKEN = ""


# ── IG account resolution ─────────────────────────────────────────────────────

def _resolve_ig_user_id() -> str:
    """Find the IG professional account linked to the token's Facebook pages.

    Uses IG_USER_ID env if provided; otherwise queries /me/accounts and takes
    the first page with a linked instagram_business_account.
    """
    global IG_USER_ID, PAGE_ID, PAGE_TOKEN
    if IG_USER_ID:
        return IG_USER_ID
    r = requests.get(
        f"{GRAPH}/me/accounts",
        params={"fields": "id,name,access_token,instagram_business_account",
                "access_token": IG_ACCESS_TOKEN},
        timeout=30,
    )
    data = r.json()
    if "data" not in data:
        raise RuntimeError(f"Could not list Facebook pages: {data.get('error', data)}")
    for page in data["data"]:
        if not PAGE_ID:  # remember first page for Facebook posting
            PAGE_ID, PAGE_TOKEN = page.get("id", ""), page.get("access_token", "")
        iba = page.get("instagram_business_account")
        if iba:
            log.info("Resolved IG account %s via page '%s' (page id %s)",
                     iba["id"], page.get("name"), page.get("id"))
            IG_USER_ID = iba["id"]
            PAGE_ID, PAGE_TOKEN = page.get("id", ""), page.get("access_token", "")
            return IG_USER_ID
    names = ", ".join(f"{p.get('name')} ({p.get('id')})" for p in data["data"]) or "none"
    raise RuntimeError(
        f"No Instagram professional account is linked to any Facebook page on this token. "
        f"Pages found: {names}. Link your IG account to a page in Meta Business settings.")


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
    # cover frame: skip the fade-in from black (ms into the video)
    thumb_offset = os.getenv("IG_THUMB_OFFSET_MS", "2000")
    r = requests.post(
        f"{GRAPH}/{IG_USER_ID}/media",
        data={"media_type": "REELS", "video_url": video_url,
              "caption": caption[:2200], "share_to_feed": "true",
              "thumb_offset": thumb_offset,
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


def _post_instagram(video_url: str, caption: str) -> str:
    log.info("Creating IG media container...")
    container = _create_container(video_url, caption)
    _wait_until_ready(container)
    media_id = _publish(container)
    log.info("Instagram Reel published: media id %s", media_id)
    return media_id


def _post_facebook(video_url: str, description: str) -> str:
    """Post the video to the Facebook Page (shows as a Reel/video on the page)."""
    if not (PAGE_ID and PAGE_TOKEN):
        raise RuntimeError(
            "No page access token — regenerate the system-user token with "
            "pages_manage_posts + publish_video permissions")
    r = requests.post(
        f"{GRAPH}/{PAGE_ID}/videos",
        data={"file_url": video_url, "description": description[:5000],
              "access_token": PAGE_TOKEN},
        timeout=120,
    )
    data = r.json()
    if "id" not in data:
        raise RuntimeError(f"Facebook video post failed: {data.get('error', data)}")
    log.info("Facebook Page video published: id %s", data["id"])
    return data["id"]


def crosspost(video_path: Path, caption: str) -> dict:
    """Host the video once, then publish to Instagram and Facebook independently.

    Returns e.g. {"instagram": "posted", "instagram_id": "...",
                  "facebook": "failed: ...", ...} — one platform failing
    never blocks the other.
    """
    if not IG_ACCESS_TOKEN:
        raise RuntimeError("Meta not configured (IG_ACCESS_TOKEN secret missing)")
    if not (GH_TOKEN and GH_REPO):
        raise RuntimeError("GH_TOKEN / GITHUB_REPOSITORY missing — cannot host video")

    _resolve_ig_user_id()
    results: dict = {}
    tag = f"reel-temp-{int(time.time())}"
    video_url, release_id = _host_on_github(Path(video_path), tag)
    try:
        if os.getenv("INSTAGRAM_ENABLED", "true").lower() == "true":
            try:
                results["instagram_id"] = _post_instagram(video_url, caption)
                results["instagram"] = "posted"
            except Exception as exc:
                log.warning("Instagram post failed (non-fatal): %s", exc)
                results["instagram"] = f"failed: {exc}"
        if os.getenv("FACEBOOK_ENABLED", "true").lower() == "true":
            try:
                results["facebook_id"] = _post_facebook(video_url, caption)
                results["facebook"] = "posted"
            except Exception as exc:
                log.warning("Facebook post failed (non-fatal): %s", exc)
                results["facebook"] = f"failed: {exc}"
    finally:
        _cleanup_github(release_id, tag)
    return results
