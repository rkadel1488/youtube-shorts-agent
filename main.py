"""
YouTube Shorts AI Agent — Main Orchestrator
============================================
Runs a daily scheduler that fires three times per day (configurable via POSTING_TIMES).
Each run:
  1. Fetches recent cricket match data + generates highlight script  (Claude)
  2. Generates SEO with tags from top-viewed cricket videos          (Claude)
  3. Fetches cricket footage from Pexels + royalty-free music        (Pexels / FreePD)
  4. Creates the video with captions, no voiceover                   (MoviePy)
  5. Uploads to YouTube                                              (YouTube Data API)

Usage:
    python main.py               # Start scheduler (runs indefinitely)
    python main.py --run-now     # Run one Short immediately (for testing)
"""
import argparse
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule

from agents.script_agent import generate_script
from agents.seo_agent import generate_seo
from agents.upload_agent import upload_video
from agents.video_agent import create_video
from config import OUTPUT_DIR, POSTING_TIMES, YOUTUBE_CATEGORY_ID
from utils.logger import get_logger

log = get_logger("main")


# ── Core pipeline ──────────────────────────────────────────────────────────────

def run_pipeline(slot: int = 0) -> dict:
    """
    Execute the full content pipeline for one cricket highlight Short.
    Returns a summary dict with all generated metadata.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id    = f"{timestamp}_slot{slot}"

    log.info("=" * 60)
    log.info("STARTING JOB: %s", job_id)
    log.info("=" * 60)

    job_dir  = OUTPUT_DIR / job_id
    temp_dir = job_dir / "temp"
    job_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    result = {"job_id": job_id, "status": "failed"}

    try:
        # ── Step 1: Generate cricket highlight script ─────────────────────────
        log.info("[1/4] Generating cricket highlight script...")
        script_data = generate_script()
        _save_json(job_dir / "script.json", script_data)
        log.info("Topic: %s", script_data["topic"])

        # ── Step 2: Generate SEO with trending tags ───────────────────────────
        log.info("[2/4] Generating SEO metadata...")
        seo_data = generate_seo(
            topic=script_data["topic"],
            hook=script_data["hook"],
        )
        _save_json(job_dir / "seo.json", seo_data)
        log.info("Title: %s", seo_data["title"])

        # ── Step 3: Create video (clips + music, no voiceover) ────────────────
        log.info("[3/4] Creating cricket highlight video...")
        video_path = create_video(
            script=script_data["script"],
            keywords=script_data.get("keywords", []),
            output_path=job_dir / "final.mp4",
            temp_dir=temp_dir,
            topic=script_data["topic"],
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
            "topic":    script_data["topic"],
        })

        _save_json(job_dir / "result.json", result)

        log.info("=" * 60)
        log.info("JOB COMPLETE: %s", result["url"])
        log.info("=" * 60)

    except Exception as exc:
        result["error"] = str(exc)
        _save_json(job_dir / "result.json", result)
        log.error("JOB FAILED (%s): %s", job_id, exc, exc_info=True)

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    return result


# ── Scheduler callbacks ────────────────────────────────────────────────────────

def _post_slot(slot: int):
    log.info("Scheduler fired — slot %d", slot)
    run_pipeline(slot=slot)


def start_scheduler():
    """Register posting times and keep the scheduler alive."""
    if len(POSTING_TIMES) < 3:
        log.warning("Less than 3 posting times configured — only %d scheduled", len(POSTING_TIMES))

    for i, t in enumerate(sorted(POSTING_TIMES)):
        schedule.every().day.at(t).do(_post_slot, slot=i)
        log.info("Scheduled slot %d at %s", i, t)

    log.info("Scheduler running. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(30)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Shorts Cricket Highlights Agent")
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run one Short immediately and exit",
    )
    parser.add_argument(
        "--slot",
        type=int,
        default=0,
        choices=[0, 1, 2],
        help="Which daily slot to run (0=morning, 1=afternoon, 2=evening).",
    )
    args = parser.parse_args()

    if args.run_now:
        result = run_pipeline(slot=args.slot)
        status = result.get("status", "failed")
        if status == "success":
            print(f"\nSuccess! Watch at: {result['url']}")
            sys.exit(0)
        else:
            print(f"\nFailed: {result.get('error', 'unknown error')}")
            sys.exit(1)
    else:
        start_scheduler()
