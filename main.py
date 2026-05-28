"""
YouTube Shorts Cricket Highlights Bot
======================================
Downloads a Creative Commons licensed cricket Short from YouTube,
adds free background music, then uploads it to the channel.

Pipeline (4 steps):
  1. Download a CC-licensed cricket Short via yt-dlp
  2. Generate SEO metadata (title, description, tags) with Claude
  3. Mix in background music (NCS / FreePD) — no voiceover
  4. Upload to YouTube

Usage:
    python main.py               # Start scheduler (runs 3x daily)
    python main.py --run-now     # Run once immediately for testing
"""
import argparse
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule

from agents.seo_agent import generate_seo
from agents.upload_agent import upload_video
from agents.video_agent import create_video
from agents.yt_shorts_agent import download_cc_cricket_short
from config import OUTPUT_DIR, POSTING_TIMES, YOUTUBE_CATEGORY_ID
from utils.logger import get_logger

log = get_logger("main")


def run_pipeline(slot: int = 0) -> dict:
    """Run one full cricket highlights pipeline. Returns a result summary dict."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id    = f"{timestamp}_slot{slot}"
    job_dir   = OUTPUT_DIR / job_id
    temp_dir  = job_dir / "temp"
    job_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("STARTING JOB: %s", job_id)
    log.info("=" * 60)

    result = {"job_id": job_id, "status": "failed"}

    try:
        # ── Step 1: Find the CC cricket Short (get metadata for SEO) ─────────
        log.info("[1/4] Searching for CC cricket Short on YouTube...")
        cc_path, video_info = download_cc_cricket_short(temp_dir)
        if not cc_path:
            raise RuntimeError("No CC cricket Short found — check yt-dlp and internet")

        topic = video_info.get("title", "Cricket Highlights")
        channel = video_info.get("channel", "")
        log.info("Found: '%s' by %s", topic, channel)
        _save_json(job_dir / "source.json", video_info)

        # ── Step 2: Generate SEO metadata ────────────────────────────────────
        log.info("[2/4] Generating SEO metadata...")
        seo_data = generate_seo(topic=topic, hook=topic)
        # Add attribution to description (CC BY requires credit)
        if channel:
            seo_data["description"] += f"\n\nOriginal footage by {channel} (CC BY licence)"
        _save_json(job_dir / "seo.json", seo_data)
        log.info("Title: %s", seo_data["title"])

        # ── Step 3: Create video (CC Short + music) ───────────────────────────
        log.info("[3/4] Creating final video with background music...")
        video_path = create_video(
            topic=topic,
            output_path=job_dir / "final.mp4",
            temp_dir=temp_dir,
            cc_path=cc_path,
        )

        # ── Step 4: Upload to YouTube ─────────────────────────────────────────
        log.info("[4/4] Uploading to YouTube...")
        video_id = upload_video(
            video_path=video_path,
            title=seo_data["title"],
            description=seo_data["description"],
            tags=seo_data["tags"],
            hashtags=seo_data["hashtags"],
            category_id=YOUTUBE_CATEGORY_ID,
        )

        result.update({
            "status":   "success",
            "video_id": video_id,
            "url":      f"https://www.youtube.com/shorts/{video_id}",
            "title":    seo_data["title"],
            "source":   topic,
        })
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
    run_pipeline(slot=slot)


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
    parser = argparse.ArgumentParser(description="Cricket Highlights YouTube Bot")
    parser.add_argument("--run-now", action="store_true",
                        help="Run one Short immediately and exit")
    parser.add_argument("--slot", type=int, default=0, choices=[0, 1, 2],
                        help="Slot to run (0=morning, 1=afternoon, 2=evening)")
    args = parser.parse_args()

    if args.run_now:
        r = run_pipeline(slot=args.slot)
        if r.get("status") == "success":
            print(f"\nDone! Watch at: {r['url']}")
            sys.exit(0)
        else:
            print(f"\nFailed: {r.get('error', 'unknown error')}")
            sys.exit(1)
    else:
        start_scheduler()
