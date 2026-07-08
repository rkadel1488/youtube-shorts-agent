"""
Runs one full content-creation pipeline (trend pick -> script -> voice ->
images -> render) then posts the result to whichever accounts the caller
specifies — each with its own credentials, pulled from the encrypted DB.

This is the dashboard's replacement for main.py's GitHub-Actions-era
single-account flow: same content agents, but fans out to N accounts.
"""
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # import sibling agents/ package

import db
from agents.audio_agent import generate_voiceover
from agents.image_agent import generate_images
from agents.instagram_agent import crosspost
from agents.script_agent import generate_trend_script
from agents.seo_agent import generate_seo
from agents.trend_agent import get_evergreen_topic, get_trend_topic
from agents.upload_agent import upload_video
from agents.video_agent import create_ai_video
from agents.video_editor import enhance_video
from utils.logger import get_logger

log = get_logger(__name__)

WORK_DIR = Path(__file__).parent / "work"
WORK_DIR.mkdir(exist_ok=True)


def _recent_history() -> dict:
    """Pull recent titles/topics from job history for dedupe, same shape
    trend_agent expects."""
    jobs = db.list_jobs(limit=150)
    titles, topics = [], []
    for j in jobs:
        if j["status"] != "success":
            continue
        if j["source"]:
            topics.append(j["source"])
        if j["result_json"]:
            try:
                import json
                seo_title = json.loads(j["result_json"]).get("seo_title")
                if seo_title:
                    titles.append(seo_title)
            except Exception:
                pass
    return {"titles": titles, "topics": topics}


def _pick_topic() -> dict:
    history = _recent_history()
    try:
        return get_trend_topic(recent_topics=history["topics"])
    except Exception as exc:
        log.warning("Trend topic failed (%s) — generating evergreen topic", exc)
    return get_evergreen_topic(recent_topics=history["topics"])


def _post_to_account(account: dict, video_path: Path, seo_data: dict) -> dict:
    """Post the rendered video to one account, returning its result dict."""
    creds = db.get_account_credentials(account["id"])
    label = account["label"]

    if account["platform"] == "youtube":
        try:
            video_id, refreshed = upload_video(
                video_path=video_path,
                title=seo_data["title"],
                description=seo_data["description"],
                tags=seo_data["tags"],
                hashtags=seo_data["hashtags"],
                category_id="28",
                token_info=creds,
            )
            if refreshed != creds:
                db.update_account_credentials(account["id"], refreshed)
            return {"account": label, "platform": "youtube", "status": "posted",
                    "url": f"https://www.youtube.com/shorts/{video_id}"}
        except Exception as exc:
            log.warning("[%s] YouTube upload failed: %s", label, exc)
            return {"account": label, "platform": "youtube", "status": f"failed: {exc}"}

    elif account["platform"] == "meta":
        caption = f"{seo_data['title']}\n\n" + " ".join(seo_data.get("hashtags", []))
        try:
            result = crosspost(
                video_path, caption, access_token=creds.get("access_token", ""),
                post_to_instagram=bool(account.get("post_to_instagram", 1)),
                post_to_facebook=bool(account.get("post_to_facebook", 1)),
            )
            result["account"] = label
            result["platform"] = "meta"
            return result
        except Exception as exc:
            log.warning("[%s] Meta cross-post failed: %s", label, exc)
            return {"account": label, "platform": "meta", "status": f"failed: {exc}"}

    return {"account": label, "platform": account["platform"], "status": "failed: unknown platform"}


def run_trend_job(account_ids: list[int]) -> dict:
    """Full pipeline: pick a trend, make the video, post to every given account."""
    accounts = [db.get_account(aid) for aid in account_ids]
    accounts = [a for a in accounts if a and a["enabled"]]
    if not accounts:
        raise ValueError("No enabled accounts given for this job")

    job_id = db.create_job("trend", account_ids, source="")
    logs = []

    def _log(msg):
        log.info(msg)
        logs.append(msg)

    job_dir = WORK_DIR / f"job_{job_id}"
    job_dir.mkdir(parents=True, exist_ok=True)

    try:
        _log("[1] Picking a trending topic...")
        topic = _pick_topic()
        _log(f"Topic: {topic['title']} [{topic['category']}]")
        db.update_job_source(job_id, topic["title"])

        _log("[2] Writing script...")
        script_data = generate_trend_script(topic, used_titles=_recent_history()["titles"])

        _log("[3] Generating voiceover...")
        audio_path = job_dir / "voice.mp3"
        generate_voiceover(script_data["script"], audio_path)

        _log("[4] Generating images...")
        images_dir = job_dir / "images"
        images = generate_images(topic=script_data["topic"],
                                 keywords=script_data["keywords"],
                                 output_dir=images_dir)
        if not images:
            raise RuntimeError("AI image generation returned no images")

        _log("[5] Assembling video...")
        raw_path = job_dir / "final_raw.mp4"
        create_ai_video(
            topic=script_data["topic"],
            image_paths=images,
            voiceover_path=audio_path,
            output_path=raw_path,
            temp_dir=job_dir,
            on_screen_hook=script_data.get("on_screen_hook"),
        )

        video_path = job_dir / "final.mp4"
        try:
            enhance_video(raw_path, video_path, job_dir)
        except Exception as exc:
            _log(f"Enhancement failed ({exc}) — using raw render")
            import shutil
            shutil.copy2(raw_path, video_path)

        _log("[6] Writing SEO metadata...")
        seo_data = generate_seo(topic=script_data["topic"], hook=script_data["hook"],
                                niche="trending news", used_titles=_recent_history()["titles"])

        _log(f"[7] Posting to {len(accounts)} account(s)...")
        results = [_post_to_account(a, video_path, seo_data) for a in accounts]

        overall_status = "success" if any(
            r.get("status") == "posted" or r.get("instagram") == "posted"
            or r.get("facebook") == "posted" for r in results
        ) else "failed"

        db.finish_job(job_id, overall_status,
                      {"topic": topic["title"], "seo_title": seo_data["title"], "results": results},
                      log_text="\n".join(logs))
        return {"job_id": job_id, "status": overall_status, "results": results}

    except Exception:
        tb = traceback.format_exc()
        logs.append(tb)
        db.finish_job(job_id, "failed", {"error": tb}, log_text="\n".join(logs))
        raise
    finally:
        # keep rendered files for ~1 day for debugging, then let a cleanup
        # cron (or manual `rm`) reclaim disk space; not deleted here so a
        # failed job's video can still be inspected/re-posted manually.
        pass


def run_clip_job(youtube_url: str, account_ids: list[int]) -> dict:
    """Turn an existing YouTube video into a Short and post it to the given accounts."""
    from clipper import clip_youtube_video

    accounts = [db.get_account(aid) for aid in account_ids]
    accounts = [a for a in accounts if a and a["enabled"]]
    if not accounts:
        raise ValueError("No enabled accounts given for this job")

    job_id = db.create_job("clip", account_ids, source=youtube_url)
    logs = []

    def _log(msg):
        log.info(msg)
        logs.append(msg)

    job_dir = WORK_DIR / f"clipjob_{job_id}"

    try:
        _log(f"[1] Clipping source video: {youtube_url}")
        clip = clip_youtube_video(youtube_url, job_dir)
        _log(f"Selected clip: {clip['hook_title']} ({clip['start_seconds']:.0f}s-{clip['end_seconds']:.0f}s)")
        db.update_job_source(job_id, f"{youtube_url} — {clip['hook_title']}")

        _log("[2] Writing SEO metadata...")
        seo_data = generate_seo(topic=clip["hook_title"], hook=clip["hook_title"],
                                niche="trending news", used_titles=_recent_history()["titles"])

        _log(f"[3] Posting to {len(accounts)} account(s)...")
        results = [_post_to_account(a, clip["video_path"], seo_data) for a in accounts]

        overall_status = "success" if any(
            r.get("status") == "posted" or r.get("instagram") == "posted"
            or r.get("facebook") == "posted" for r in results
        ) else "failed"

        db.finish_job(job_id, overall_status,
                      {"source_url": youtube_url, "hook_title": clip["hook_title"],
                       "seo_title": seo_data["title"], "results": results},
                      log_text="\n".join(logs))
        return {"job_id": job_id, "status": overall_status, "results": results}

    except Exception:
        tb = traceback.format_exc()
        logs.append(tb)
        db.finish_job(job_id, "failed", {"error": tb}, log_text="\n".join(logs))
        raise
