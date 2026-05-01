"""
YouTube Shorts AI Agent — Main Orchestrator
============================================
Runs a daily scheduler that fires twice per day (configurable via POSTING_TIMES).
Each run:
  1. Picks the niche for this slot
  2. Generates a script  (Claude)
  3. Generates SEO       (Claude)
  4. Generates voiceover (ElevenLabs)
  5. Creates the video   (Pexels + MoviePy)
  6. Uploads to YouTube  (YouTube Data API)

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

from agents.audio_agent import generate_voiceover
from agents.script_agent import generate_script
from agents.seo_agent import generate_seo
from agents.upload_agent import upload_video
from agents.video_agent import create_video
from config import NICHES, OUTPUT_DIR, POSTING_TIMES
from utils.logger import get_logger

log = get_logger("main")

# ── Niche rotation ─────────────────────────────────────────────────────────────
# Each day has 2 posting slots (AM=0, PM=1).
# Niche index = (day_of_year * 2 + slot) % len(NICHES)

def _pick_niche(slot: int) -> dict:
    day = datetime.now().timetuple().tm_yday
    index = (day * 2 + slot) % len(NICHES)
    return NICHES[index]


def _current_slot() -> int:
    """Return 0 for the first daily post, 1 for the second."""
    hour = datetime.now().hour
    times = sorted(POSTING_TIMES)
    if len(times) < 2:
        return 0
    threshold_hour = int(times[0].split(":")[0])
    second_hour = int(times[1].split(":")[0])
    if hour >= second_hour:
        return 1
    return 0


# ── Core pipeline ──────────────────────────────────────────────────────────────

def run_pipeline(slot: int = 0) -> dict:
    """
    Execute the full content pipeline for one Short.
    Returns a summary dict with all generated metadata.
    """
    niche = _pick_niche(slot)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id = f"{timestamp}_{niche['name']}"

    log.info("=" * 60)
    log.info("STARTING JOB: %s | Niche: %s", job_id, niche["label"])
    log.info("=" * 60)

    # Working directories for this job
    job_dir = OUTPUT_DIR / job_id
    temp_dir = job_dir / "temp"
    job_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    result = {"job_id": job_id, "niche": niche["label"], "status": "failed"}

    try:
        # ── Step 1: Generate script ───────────────────────────────────────────
        log.info("[1/5] Generating script…")
        script_data = generate_script(niche)
        _save_json(job_dir / "script.json", script_data)
        log.info("Topic: %s", script_data["topic"])

        # ── Step 2: Generate SEO ──────────────────────────────────────────────
        log.info("[2/5] Generating SEO metadata…")
        seo_data = generate_seo(
            niche=niche,
            topic=script_data["topic"],
            hook=script_data["hook"],
        )
        _save_json(job_dir / "seo.json", seo_data)
        log.info("Title: %s", seo_data["title"])

        # ── Step 3: Generate voiceover ────────────────────────────────────────
        log.info("[3/5] Generating voiceover…")
        audio_path = generate_voiceover(
            script=script_data["script"],
            output_path=job_dir / "voiceover.mp3",
        )

        # ── Step 4: Create video ──────────────────────────────────────────────
        log.info("[4/5] Creating video...")
        video_path = create_video(
            script=script_data["script"],
            audio_path=audio_path,
            keywords=niche["search_terms"] + script_data.get("keywords", []),
            output_path=job_dir / "final.mp4",
            temp_dir=temp_dir,
            topic=script_data["topic"],
            niche=niche,
        )

        # ── Step 5: Upload to YouTube ─────────────────────────────────────────
        log.info("[5/5] Uploading to YouTube…")
        video_id = upload_video(
            video_path=video_path,
            title=seo_data["title"],
            description=seo_data["description"],
            tags=seo_data["tags"],
            hashtags=seo_data["hashtags"],
            category_id=niche["category_id"],
        )

        result.update(
            {
                "status": "success",
                "video_id": video_id,
                "url": f"https://www.youtube.com/shorts/{video_id}",
                "title": seo_data["title"],
                "topic": script_data["topic"],
            }
        )
        _save_json(job_dir / "result.json", result)

        log.info("=" * 60)
        log.info("JOB COMPLETE: %s", result["url"])
        log.info("=" * 60)

    except Exception as exc:
        result["error"] = str(exc)
        _save_json(job_dir / "result.json", result)
        log.error("JOB FAILED (%s): %s", job_id, exc, exc_info=True)

    finally:
        # Clean up temp clips/files but keep final outputs
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    return result


# ── Scheduler callbacks ────────────────────────────────────────────────────────

def _post_slot(slot: int):
    log.info("Scheduler fired — slot %d", slot)
    run_pipeline(slot=slot)


def start_scheduler():
    """Register posting times and keep the scheduler alive."""
    if len(POSTING_TIMES) < 2:
        log.warning("Less than 2 posting times configured — only %d scheduled", len(POSTING_TIMES))

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
    parser = argparse.ArgumentParser(description="YouTube Shorts AI Agent")
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run one Short immediately (slot 0) and exit",
    )
    parser.add_argument(
        "--slot",
        type=int,
        default=0,
        choices=[0, 1],
        help="Which daily slot to run (0=AM, 1=PM). Only used with --run-now",
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
