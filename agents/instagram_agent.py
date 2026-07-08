"""
Cross-posts a rendered video to Instagram Reels and a Facebook Page via the
Meta Graph API.

Stateless / per-call: every function takes the target account's access_token
explicitly and resolves its IG user id + Page id fresh each call. This is
required for multi-account support — a module-level cache (the old design)
would leak account A's resolved IDs into account B's requests.

Instagram cannot accept file uploads — it downloads the video from a public
URL. This agent temporarily hosts the video as a GitHub release asset on the
DASHBOARD'S OWN repo (GH_TOKEN/GH_REPO — infra-level, not per-target-account),
tells Instagram to fetch it, waits for processing, publishes, then deletes
the release. Facebook Reels upload the local file directly (no hosting needed).
"""
import os
import time
from pathlib import Path

import requests

from utils.logger import get_logger

log = get_logger(__name__)

GRAPH = "https://graph.facebook.com/v21.0"
GH_API = "https://api.github.com"

GH_TOKEN = os.getenv("GH_TOKEN", "")
GH_REPO = os.getenv("GITHUB_REPOSITORY", "")


# ── account resolution (stateless — no caching across accounts) ──────────────

def resolve_meta_account(access_token: str) -> dict:
    """Find the Page + linked IG business account for this specific token.

    Returns {"ig_user_id": str|None, "page_id": str|None, "page_token": str|None}.
    Raises if the token can't list any pages at all.
    """
    r = requests.get(
        f"{GRAPH}/me/accounts",
        params={"fields": "id,name,access_token,instagram_business_account",
                "access_token": access_token},
        timeout=30,
    )
    data = r.json()
    if "data" not in data:
        raise RuntimeError(f"Could not list Facebook pages: {data.get('error', data)}")

    result = {"ig_user_id": None, "page_id": None, "page_token": None}
    for page in data["data"]:
        if result["page_id"] is None:
            result["page_id"] = page.get("id", "")
            result["page_token"] = page.get("access_token", "")
        iba = page.get("instagram_business_account")
        if iba:
            result["ig_user_id"] = iba["id"]
            result["page_id"] = page.get("id", "")
            result["page_token"] = page.get("access_token", "")
            log.info("Resolved IG account %s via page '%s' (page id %s)",
                     iba["id"], page.get("name"), page.get("id"))
            break
    if not result["page_id"]:
        names = ", ".join(f"{p.get('name')} ({p.get('id')})" for p in data["data"]) or "none"
        raise RuntimeError(f"No Facebook pages found on this token. Pages: {names}")
    return result


# ── temporary public hosting via GitHub release asset (for Instagram only) ───

def _gh_headers() -> dict:
    return {"Authorization": f"token {GH_TOKEN}",
            "Accept": "application/vnd.github+json"}


def _host_on_github(video_path: Path, tag: str) -> tuple[str, int]:
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
    except Exception as exc:
        log.warning("Release cleanup failed (harmless): %s", exc)


# ── Instagram Graph API publish flow ──────────────────────────────────────────

def _create_container(ig_user_id: str, access_token: str, video_url: str, caption: str) -> str:
    thumb_offset = os.getenv("IG_THUMB_OFFSET_MS", "2000")
    r = requests.post(
        f"{GRAPH}/{ig_user_id}/media",
        data={"media_type": "REELS", "video_url": video_url,
              "caption": caption[:2200], "share_to_feed": "true",
              "thumb_offset": thumb_offset, "access_token": access_token},
        timeout=60,
    )
    data = r.json()
    if "id" not in data:
        raise RuntimeError(f"IG container creation failed: {data.get('error', data)}")
    return data["id"]


def _wait_until_ready(container_id: str, access_token: str, timeout_s: int = 300) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = requests.get(
            f"{GRAPH}/{container_id}",
            params={"fields": "status_code,status", "access_token": access_token},
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


def _publish(ig_user_id: str, access_token: str, container_id: str) -> str:
    r = requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": access_token},
        timeout=60,
    )
    data = r.json()
    if "id" not in data:
        raise RuntimeError(f"IG publish failed: {data.get('error', data)}")
    return data["id"]


def post_instagram(access_token: str, ig_user_id: str, video_url: str, caption: str) -> str:
    log.info("Creating IG media container...")
    container = _create_container(ig_user_id, access_token, video_url, caption)
    _wait_until_ready(container, access_token)
    media_id = _publish(ig_user_id, access_token, container)
    log.info("Instagram Reel published: media id %s", media_id)
    return media_id


def post_facebook(page_id: str, page_token: str, video_path: Path, description: str) -> str:
    """Publish a genuine Facebook Reel via the dedicated video_reels endpoint.

    /{page-id}/videos creates a regular Video post that Facebook may LABEL
    "Reel" in the library UI without placing it in the actual Reels
    algorithmic feed (near-zero organic reach). /{page-id}/video_reels is
    the real Reels publishing API. Three-phase resumable upload.
    """
    video_path = Path(video_path)

    r = requests.post(f"{GRAPH}/{page_id}/video_reels",
                      data={"upload_phase": "start", "access_token": page_token},
                      timeout=30)
    start = r.json()
    if "video_id" not in start:
        raise RuntimeError(f"Reel upload start failed: {start.get('error', start)}")
    video_id, upload_url = start["video_id"], start["upload_url"]

    file_size = video_path.stat().st_size
    with open(video_path, "rb") as f:
        r = requests.post(
            upload_url,
            headers={"Authorization": f"OAuth {page_token}",
                     "offset": "0", "file_size": str(file_size)},
            data=f.read(),
            timeout=300,
        )
    if not r.ok:
        raise RuntimeError(f"Reel video upload failed: {r.status_code} {r.text[:300]}")

    r = requests.post(
        f"{GRAPH}/{page_id}/video_reels",
        data={"upload_phase": "finish", "video_id": video_id,
              "video_state": "PUBLISHED", "description": description[:5000],
              "access_token": page_token},
        timeout=60,
    )
    finish = r.json()
    if finish.get("success") is False or "error" in finish:
        raise RuntimeError(f"Reel publish failed: {finish.get('error', finish)}")
    log.info("Facebook Reel published (native Reels feed): video id %s", video_id)
    return video_id


def crosspost(video_path: Path, caption: str, access_token: str,
              post_to_instagram: bool = True, post_to_facebook: bool = True) -> dict:
    """Resolve this account's Page/IG ids fresh, then publish independently.

    Returns e.g. {"instagram": "posted", "instagram_id": "...",
                  "facebook": "failed: ...", ...} — one platform failing
    never blocks the other. Safe to call concurrently for different accounts
    (no shared mutable state).
    """
    if not access_token:
        raise RuntimeError("Meta access_token missing for this account")
    if not (GH_TOKEN and GH_REPO):
        raise RuntimeError("GH_TOKEN / GITHUB_REPOSITORY missing — cannot host video for IG")

    account = resolve_meta_account(access_token)
    results: dict = {}
    video_path = Path(video_path)

    release_id = tag = video_url = None
    try:
        if post_to_instagram and account["ig_user_id"]:
            tag = f"reel-temp-{int(time.time())}"
            video_url, release_id = _host_on_github(video_path, tag)
            try:
                results["instagram_id"] = post_instagram(
                    access_token, account["ig_user_id"], video_url, caption)
                results["instagram"] = "posted"
            except Exception as exc:
                log.warning("Instagram post failed (non-fatal): %s", exc)
                results["instagram"] = f"failed: {exc}"
        elif post_to_instagram:
            results["instagram"] = "failed: no Instagram account linked to this Page"

        if post_to_facebook and account["page_id"]:
            try:
                results["facebook_id"] = post_facebook(
                    account["page_id"], account["page_token"], video_path, caption)
                results["facebook"] = "posted"
            except Exception as exc:
                log.warning("Facebook post failed (non-fatal): %s", exc)
                results["facebook"] = f"failed: {exc}"
    finally:
        if release_id:
            _cleanup_github(release_id, tag)
    return results
