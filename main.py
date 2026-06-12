"""
YouTube Shorts Cricket Highlights Bot
======================================
Downloads Creative Commons licensed cricket clips from YouTube,
assembles them into a '3 Moments' compilation Short with AI voiceover,
FFmpeg color grading, and trend-based SEO. Falls back to AI-generated
niche video if fewer than 2 CC clips found.

Pipeline:
  0. Load history (used titles/topics/video_ids) to avoid repeats
  1. Trend analysis — find top-viewed cricket Shorts, extract tags/hooks
  2. Download CC-licensed cricket clips via yt-dlp
  3. Generate trend-based script + Gemini TTS voiceover
  4. Build compilation (CC clips + voiceover + music)
  5. FFmpeg color grade + fade enhancement
  6. Generate SEO using tags from top-viewed videos
  7. Upload to YouTube
  8. Save updated history back to state/history.json

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
from agents.script_agent import generate_niche_script, generate_trend_script
from agents.seo_agent import generate_seo
from agents.trend_analyzer import analyze_top_videos
from agents.upload_agent import upload_video
from agents.video_agent import create_ai_video, create_cricket_compilation
from agents.video_editor import enhance_video
from agents.yt_shorts_agent import download_cc_cricket_clips
from config import OUTPUT_DIR, POSTING_TIMES, YOUTUBE_CATEGORY_ID
from utils.logger import get_logger

log = get_logger("main")

FALLBACK_NICHES = ["fun_facts", "horror_story", "football"]
HISTORY_PATH = Path(__file__).parent / "state" / "history.json"
HISTORY_MAX = 150  # how many past entries to keep per field


# ── history helpers ───────────────────────────────────────────────────────────

def _load_history() -> dict:
    try:
        if HISTORY_PATH.exists():
            with open(HISTORY_PATH, encoding="utf-8") as f:
                h = json.load(f)
            log.info("History: %d used titles, %d used video_ids",
                     len(h.get("titles", [])), len(h.get("video_ids", [])))
            return h
    except Exception as exc:
        log.warning("Could not load history: %s — starting fresh", exc)
    return {"titles": [], "topics": [], "video_ids": []}


def _save_history(history: dict):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Trim old entries so the file doesn't grow unbounded
    for key in ("titles", "topics", "video_ids"):
        history[key] = history.get(key, [])[-HISTORY_MAX:]
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    log.info("History saved: %d titles, %d video_ids",
             len(history["titles"]), len(history["video_ids"]))


def _update_history(history: dict, title: str, topic: str, video_ids: list):
    if title and title not in history["titles"]:
        history["titles"].append(title)
    if topic and topic not in history["topics"]:
        history["topics"].append(topic)
    for vid in video_ids:
        if vid and vid not in history["video_ids"]:
            history["video_ids"].append(vid)
    _save_history(history)


# ── AI fallback pipeline ──────────────────────────────────────────────────────

def _run_ai_pipeline(
    slot: int,
    job_dir: Path,
    temp_dir: Path,
    result: dict,
    history: dict,
    trend_data: dict = None,
) -> dict:
    """
    AI-generated fallback pipeline — used when no real footage is found.
    Generates a script, images, voiceover, and video for a rotating niche.
    Skips niches whose recent topics are all used; cycles to the next fresh one.
    """
    day_of_year = datetime.now().timetuple().tm_yday
    niche = FALLBACK_NICHES[(day_of_year + slot) % len(FALLBACK_NICHES)]
    log.info("No real footage found — switching to AI pipeline (niche=%s)", niche)

    log.info("[AI-1/4] Generating %s script...", niche)
    used_titles = history.get("titles", [])
    used_topics = history.get("topics", [])
    script_data = generate_niche_script(
        niche, used_titles=used_titles, used_topics=used_topics
    )
    _save_json(job_dir / "script.json", script_data)

    images_dir = temp_dir / "images"
    vo_path = temp_dir / "voiceover.mp3"

    log.info("[AI-2/4] Generating AI images...")
    images = generate_images(
        topic=script_data["topic"],
        keywords=script_data["keywords"],
        output_dir=images_dir,
    )
    if not images:
        raise RuntimeError("AI image generation returned no images")

    log.info("[AI-3/4] Generating voiceover...")
    generate_voiceover(script_data["script"], vo_path)

    log.info("[AI-4/4] Assembling AI video...")
    raw_path = job_dir / "final_raw.mp4"
    create_ai_video(
        topic=script_data["topic"],
        image_paths=images,
        voiceover_path=vo_path,
        output_path=raw_path,
        temp_dir=temp_dir,
        on_screen_hook=script_data.get("on_screen_hook"),
    )

    log.info("[AI-4b] Enhancing with FFmpeg...")
    final_path = job_dir / "final.mp4"
    try:
        enhance_video(raw_path, final_path, temp_dir)
    except Exception as exc:
        log.warning("Enhancement failed: %s — using raw", exc)
        shutil.copy2(raw_path, final_path)
    video_path = final_path

    log.info("[AI-SEO] Generating SEO metadata...")
    seo_data = generate_seo(
        topic=script_data["topic"],
        hook=script_data["hook"],
        niche=niche,
        trend_data=trend_data,
        used_titles=used_titles,
    )
    _save_json(job_dir / "seo.json", seo_data)
    log.info("Title: %s", seo_data["title"])

    log.info("[AI-Upload] Uploading to YouTube...")
    video_id = upload_video(
        video_path=video_path,
        title=seo_data["title"],
        description=seo_data["description"],
        tags=seo_data["tags"],
        hashtags=seo_data["hashtags"],
        category_id=YOUTUBE_CATEGORY_ID,
    )

    _update_history(history, seo_data["title"], script_data["topic"], [])

    result.update({
        "status":   "success",
        "video_id": video_id,
        "url":      f"https://www.youtube.com/shorts/{video_id}",
        "title":    seo_data["title"],
        "source":   script_data["topic"],
        "niche":    niche,
    })
    _save_json(job_dir / "result.json", result)

    log.info("=" * 60)
    log.info("SUCCESS (AI pipeline): %s", result["url"])
    log.info("=" * 60)

    return result


# ── main pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(slot: int = 0) -> dict:
    """Run one full pipeline. Falls back to AI-generated content if fewer than 2 CC cricket clips found."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id    = f"{timestamp}_slot{slot}"
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
        # ── Step 0: Trend analysis ────────────────────────────────────────────
        log.info("[0] Analyzing top-viewed cricket Shorts for trends...")
        trend_data = {}
        try:
            trend_data = analyze_top_videos()
            log.info("Trend data: %d tags, top video: %s",
                     len(trend_data.get("tags", [])), trend_data.get("top_title", "")[:50])
        except Exception as exc:
            log.warning("Trend analysis failed: %s — continuing without trend data", exc)

        # ── Step 1: Download CC cricket clips (skip already-used IDs) ─────────
        log.info("[1] Downloading CC cricket clips for compilation...")
        used_video_ids = set(history.get("video_ids", []))
        clips, clip_infos = download_cc_cricket_clips(
            temp_dir, count=3, skip_ids=used_video_ids
        )

        if not clips:
            log.info("Insufficient CC cricket clips — switching to AI pipeline")
            return _run_ai_pipeline(slot=slot, job_dir=job_dir, temp_dir=temp_dir,
                                    result=result, history=history, trend_data=trend_data)

        # ── Step 2: Generate trend-based script + voiceover ───────────────────
        n = len(clips)
        topic = f"{n} Insane Cricket Moments"
        channels = list({i["channel"] for i in clip_infos if i.get("channel")})

        log.info("[2a] Generating trend-based commentary script...")
        vo_path = None
        script_data = {}
        try:
            script_data = generate_trend_script(
                trend_data,
                used_titles=history.get("titles", []),
                used_topics=history.get("topics", []),
            )
            _save_json(job_dir / "script.json", script_data)
            vo_path = temp_dir / "voiceover.mp3"
            log.info("[2b] Generating Gemini TTS voiceover...")
            generate_voiceover(script_data["script"], vo_path)
        except Exception as exc:
            log.warning("Script/voiceover failed: %s — compilation will use music only", exc)
            vo_path = None

        # ── Step 3: Generate SEO using trend tags ─────────────────────────────
        log.info("[3] Generating SEO metadata from trending tags...")
        seo_data = generate_seo(
            topic=topic,
            hook=f"{n} cricket moments you won't believe",
            niche="cricket",
            trend_data=trend_data,
            used_titles=history.get("titles", []),
        )
        if channels:
            seo_data["description"] += f"\n\nOriginal footage by: {', '.join(channels)} (CC BY licence)"
        _save_json(job_dir / "seo.json", seo_data)
        log.info("Title: %s", seo_data["title"])

        # ── Step 4: Build compilation with voiceover + music ──────────────────
        log.info("[4] Building cricket compilation video...")
        raw_path = job_dir / "final_raw.mp4"
        create_cricket_compilation(
            clips=clips,
            clip_infos=clip_infos,
            output_path=raw_path,
            temp_dir=temp_dir,
            voiceover_path=vo_path,
            on_screen_hook=script_data.get("on_screen_hook"),
        )

        # ── Step 4b: FFmpeg enhancement (color grade + fades) ─────────────────
        log.info("[4b] Enhancing with FFmpeg (color grade + fades)...")
        final_path = job_dir / "final.mp4"
        try:
            enhance_video(raw_path, final_path, temp_dir)
        except Exception as exc:
            log.warning("Enhancement failed: %s — using raw video", exc)
            shutil.copy2(raw_path, final_path)
        video_path = final_path

        # ── Step 5: Upload to YouTube ─────────────────────────────────────────
        log.info("[5] Uploading to YouTube...")
        video_id = upload_video(
            video_path=video_path,
            title=seo_data["title"],
            description=seo_data["description"],
            tags=seo_data["tags"],
            hashtags=seo_data["hashtags"],
            category_id=YOUTUBE_CATEGORY_ID,
        )

        used_clip_ids = [i.get("video_id", "") for i in clip_infos]
        _update_history(history, seo_data["title"], topic, used_clip_ids)

        result.update({
            "status":   "success",
            "video_id": video_id,
            "url":      f"https://www.youtube.com/shorts/{video_id}",
            "title":    seo_data["title"],
            "source":   topic,
            "niche":    "cricket",
            "clips":    n,
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
