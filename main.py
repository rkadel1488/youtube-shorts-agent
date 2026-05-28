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

from agents.audio_agent import generate_voiceover
from agents.image_agent import generate_images
from agents.script_agent import generate_niche_script
from agents.seo_agent import generate_seo
from agents.upload_agent import upload_video
from agents.video_agent import create_ai_video, create_video
from agents.yt_shorts_agent import download_cc_cricket_short
from config import OUTPUT_DIR, POSTING_TIMES, YOUTUBE_CATEGORY_ID
from utils.logger import get_logger

log = get_logger("main")

FALLBACK_NICHES = ["fun_facts", "horror_story", "football"]


def _run_ai_pipeline(
    slot: int,
    job_dir: Path,
    temp_dir: Path,
    result: dict,
) -> dict:
    """
    AI-generated fallback pipeline — used when no real footage is found.
    Generates a script, images, voiceover, and video for a rotating niche.
    """
    day_of_year = datetime.now().timetuple().tm_yday
    niche = FALLBACK_NICHES[(day_of_year + slot) % len(FALLBACK_NICHES)]
    log.info("No real footage found — switching to AI pipeline (niche=%s)", niche)

    # Generate niche script
    log.info("[AI-1/4] Generating %s script...", niche)
    script_data = generate_niche_script(niche)
    _save_json(job_dir / "script.json", script_data)

    images_dir = temp_dir / "images"
    vo_path = temp_dir / "voiceover.mp3"

    # Generate 4 AI images
    log.info("[AI-2/4] Generating AI images...")
    images = generate_images(
        topic=script_data["topic"],
        keywords=script_data["keywords"],
        output_dir=images_dir,
    )
    if not images:
        raise RuntimeError("AI image generation returned no images")

    # Generate voiceover
    log.info("[AI-3/4] Generating voiceover...")
    generate_voiceover(script_data["script"], vo_path)

    # Assemble AI video
    log.info("[AI-4/4] Assembling AI video...")
    video_path = create_ai_video(
        topic=script_data["topic"],
        image_paths=images,
        voiceover_path=vo_path,
        output_path=job_dir / "final.mp4",
        temp_dir=temp_dir,
    )

    # Generate SEO
    log.info("[AI-SEO] Generating SEO metadata...")
    seo_data = generate_seo(
        topic=script_data["topic"],
        hook=script_data["hook"],
        niche=niche,
    )
    _save_json(job_dir / "seo.json", seo_data)
    log.info("Title: %s", seo_data["title"])

    # Upload to YouTube
    log.info("[AI-Upload] Uploading to YouTube...")
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
        "source":   f"AI ({niche})",
        "niche":    niche,
    })
    _save_json(job_dir / "result.json", result)

    log.info("=" * 60)
    log.info("SUCCESS (AI pipeline): %s", result["url"])
    log.info("=" * 60)

    return result


def run_pipeline(slot: int = 0) -> dict:
    """Run one full pipeline. Falls back to AI-generated content if no real footage found."""
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
        # ── Step 1: Find the CC cricket/football Short ────────────────────────
        log.info("[1/4] Searching for CC cricket Short on YouTube...")
        cc_path, video_info = download_cc_cricket_short(temp_dir)

        if not cc_path:
            # No real footage — run the AI fallback pipeline instead
            return _run_ai_pipeline(slot=slot, job_dir=job_dir, temp_dir=temp_dir, result=result)

        topic   = video_info.get("title", "Cricket Highlights")
        channel = video_info.get("channel", "")
        niche   = video_info.get("niche", "cricket")
        log.info("Found: '%s' by %s (niche=%s)", topic, channel, niche)
        _save_json(job_dir / "source.json", video_info)

        # ── Step 2: Generate SEO metadata ────────────────────────────────────
        log.info("[2/4] Generating SEO metadata...")
        seo_data = generate_seo(topic=topic, hook=topic, niche=niche)
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
            "niche":    niche,
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
