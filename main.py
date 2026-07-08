"""
YouTube Shorts Trend Agent
===========================
Turns live trending topics into AI-narrated YouTube Shorts:
trends → factual script → AI images → Gemini TTS voiceover →
MoviePy video → FFmpeg enhancement → SEO → upload.

Topics come from Google Trends (with real news headlines) and Reddit,
deduped against state/history.json. If all trend sources fail, an
evergreen well-established-facts topic is generated instead, so a
scheduled run never fails for lack of a topic.

Pipeline:
  0. Load history (used titles/topics)
  1. Pick a trending topic (evergreen fallback)
  2. Generate factual script via Claude + Gemini TTS voiceover
  3. Generate AI images + assemble video
  4. FFmpeg color grade + fade enhancement
  5. Generate SEO metadata
  6. Upload to YouTube
  7. Save updated history + topic queue position

Usage:
    python main.py               # Start scheduler (runs 4x daily)
    python main.py --run-now     # Run once immediately for testing
"""
import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import schedule

from agents.audio_agent import generate_voiceover
from agents.image_agent import generate_images
from agents.script_agent import generate_trend_script
from agents.trend_agent import get_evergreen_topic, get_trend_topic
from agents.seo_agent import generate_seo
from agents.upload_agent import upload_video_from_files
from agents.video_agent import create_ai_video
from agents.video_editor import enhance_video
from config import OUTPUT_DIR, POSTING_TIMES, YOUTUBE_CATEGORY_ID, YOUTUBE_TOKEN_FILE
from utils.logger import get_logger

log = get_logger("main")

HISTORY_PATH = Path(__file__).parent / "state" / "history.json"
HISTORY_MAX = 400  # ~100 days of topics at 4/day — dedupe memory


# ── history helpers ───────────────────────────────────────────────────────────

def _load_history() -> dict:
    try:
        if HISTORY_PATH.exists():
            with open(HISTORY_PATH, encoding="utf-8") as f:
                h = json.load(f)
            log.info("History: %d used titles", len(h.get("titles", [])))
            return h
    except Exception as exc:
        log.warning("Could not load history: %s — starting fresh", exc)
    return {"titles": [], "topics": []}


def _save_history(history: dict):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    for key in ("titles", "topics"):
        history[key] = history.get(key, [])[-HISTORY_MAX:]
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    log.info("History saved: %d titles", len(history["titles"]))


def _update_history(history: dict, title: str, topic: str):
    if title and title not in history["titles"]:
        history["titles"].append(title)
    if topic and topic not in history["topics"]:
        history["topics"].append(topic)
    _save_history(history)


# ── topic selection ───────────────────────────────────────────────────────────

def _next_topic(history: dict) -> dict:
    """Live trending topic; evergreen established-facts topic as fallback."""
    recent = history.get("topics", [])
    try:
        return get_trend_topic(recent_topics=recent)
    except Exception as exc:
        log.warning("Trend topic failed (%s) — generating evergreen topic", exc)
    return get_evergreen_topic(recent_topics=recent)


# ── main pipeline ─────────────────────────────────────────────────────────────

def run_pipeline() -> dict:
    """Run one full pipeline for the next trending/evergreen topic."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    job_id    = timestamp
    job_dir   = OUTPUT_DIR / job_id
    temp_dir  = job_dir / "temp"
    job_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("STARTING JOB: %s", job_id)
    log.info("=" * 60)

    result  = {"job_id": job_id, "status": "failed"}
    history = _load_history()

    try:
        topic = _next_topic(history)

        log.info("[1] Generating script for '%s' [%s]...", topic["title"], topic["category"])
        script_data = generate_trend_script(topic, used_titles=history.get("titles", []))
        _save_json(job_dir / "script.json", script_data)

        images_dir = temp_dir / "images"
        vo_path = temp_dir / "voiceover.mp3"

        log.info("[2] Generating AI images...")
        images = generate_images(
            topic=script_data["topic"],
            keywords=script_data["keywords"],
            output_dir=images_dir,
        )
        if not images:
            raise RuntimeError("AI image generation returned no images")

        log.info("[3] Generating voiceover...")
        generate_voiceover(script_data["script"], vo_path)

        log.info("[4] Assembling video...")
        raw_path = job_dir / "final_raw.mp4"
        create_ai_video(
            topic=script_data["topic"],
            image_paths=images,
            voiceover_path=vo_path,
            output_path=raw_path,
            temp_dir=temp_dir,
            on_screen_hook=script_data.get("on_screen_hook"),
        )

        log.info("[4b] Enhancing with FFmpeg...")
        final_path = job_dir / "final.mp4"
        try:
            enhance_video(raw_path, final_path, temp_dir)
        except Exception as exc:
            log.warning("Enhancement failed: %s — using raw", exc)
            shutil.copy2(raw_path, final_path)

        log.info("[5] Generating SEO metadata...")
        seo_data = generate_seo(
            topic=script_data["topic"],
            hook=script_data["hook"],
            niche="trending news",
            used_titles=history.get("titles", []),
        )
        _save_json(job_dir / "seo.json", seo_data)
        log.info("Title: %s", seo_data["title"])

        log.info("[6] Uploading to YouTube...")
        video_id = upload_video_from_files(
            video_path=final_path,
            title=seo_data["title"],
            description=seo_data["description"],
            tags=seo_data["tags"],
            hashtags=seo_data["hashtags"],
            category_id=YOUTUBE_CATEGORY_ID,
            token_file=YOUTUBE_TOKEN_FILE,
        )

        _update_history(history, seo_data["title"], script_data["topic"])

        result.update({
            "status":   "success",
            "video_id": video_id,
            "url":      f"https://www.youtube.com/shorts/{video_id}",
            "title":    seo_data["title"],
            "source":   script_data["topic"],
            "topic_id": topic.get("id", 0),
            "category": topic["category"],
        })

        # [7] Cross-post to Instagram + Facebook (optional, never fatal)
        if (os.getenv("INSTAGRAM_ENABLED", "true").lower() == "true"
                or os.getenv("FACEBOOK_ENABLED", "true").lower() == "true"):
            try:
                from agents.instagram_agent import crosspost
                log.info("[7] Cross-posting to Instagram/Facebook...")
                caption = f"{seo_data['title']}\n\n" + " ".join(seo_data.get("hashtags", []))
                result.update(crosspost(final_path, caption,
                                        access_token=os.getenv("IG_ACCESS_TOKEN", "")))
            except Exception as exc:
                log.warning("Meta cross-post skipped/failed (non-fatal): %s", exc)
                result["meta_crosspost"] = f"failed: {exc}"

        _save_json(job_dir / "result.json", result)

        log.info("=" * 60)
        log.info("SUCCESS: %s", result["url"])
        log.info("=" * 60)

    except Exception as exc:
        result["error"] = str(exc)
        _save_json(job_dir / "result.json", result)
        log.error("JOB FAILED (%s): %s", job_id, exc, exc_info=True)

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    return result


def _post_slot(slot: int):
    log.info("Scheduler fired — slot %d", slot)
    run_pipeline()


def start_scheduler():
    if len(POSTING_TIMES) < 3:
        log.warning("Only %d posting times configured", len(POSTING_TIMES))
    for i, t in enumerate(sorted(POSTING_TIMES)):
        schedule.every().day.at(t).do(_post_slot, slot=i)
        log.info("Scheduled slot %d at %s UTC", i, t)
    log.info("Scheduler running — press Ctrl+C to stop")
    while True:
        schedule.run_pending()
        time.sleep(30)


def _save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Shorts Trend Bot")
    parser.add_argument("--run-now", action="store_true",
                        help="Run one Short immediately and exit")
    args = parser.parse_args()

    if args.run_now:
        r = run_pipeline()
        if r.get("status") == "success":
            print(f"\nDone! Watch at: {r['url']}")
            sys.exit(0)
        else:
            print(f"\nFailed: {r.get('error', 'unknown error')}")
            sys.exit(1)
    else:
        start_scheduler()
