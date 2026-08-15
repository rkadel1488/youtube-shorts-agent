"""
YouTube Story Video Agent
==========================
Posts ~2-minute landscape YouTube videos from a fixed pool of 200 story topics.

Pipeline:
  0. Load history (used titles) + topic queue position
  1. Pick the next unused story topic (round-robin, no repeats)
  2. Generate ~2-min script via Claude + Gemini TTS voiceover
  3. Generate 8 landscape stock images (Pexels) + assemble video
  4. FFmpeg color grade + fade enhancement
  5. Generate SEO metadata + custom thumbnail
  6. Upload video + thumbnail to YouTube
  7. Save updated history + topic queue position

Usage:
    python main.py               # Start scheduler (runs 4x daily)
    python main.py --run-now     # Run once immediately for testing
    python main.py --run-now --slot 2   # slot 0=night 1=morning 2=afternoon 3=evening
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import schedule

from agents.audio_agent import generate_voiceover
from agents.image_agent import generate_images
from agents.cartoon_image_agent import generate_cartoon_images
from agents.script_agent import generate_animated_kids_script, generate_kids_script, generate_story_script
from agents.seo_agent import generate_animated_kids_seo, generate_kids_seo, generate_seo
from agents.storyboard_agent import generate_storyboard
from agents.thumbnail_agent import create_thumbnail
from agents.upload_agent import upload_thumbnail, upload_video
from agents.veo_agent import generate_veo_clips
from agents.video_agent import create_ai_video, create_animated_kids_video, create_veo_video
from agents.video_editor import enhance_video
from config import CONTENT_TYPE, OUTPUT_DIR, POSTING_TIMES, YOUTUBE_CATEGORY_ID
from kids_topics import KIDS_TOPICS
from story_topics import STORY_TOPICS
from utils.logger import get_logger

log = get_logger("main")

HISTORY_PATH = Path(__file__).parent / "state" / "history.json"
TOPIC_STATE_PATH = Path(__file__).parent / "state" / "topic_state.json"
KIDS_TOPIC_STATE_PATH = Path(__file__).parent / "state" / "kids_topic_state.json"
HISTORY_MAX = 150


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


# ── topic queue helpers ────────────────────────────────────────────────────────

def _load_next_topic_index() -> int:
    try:
        if TOPIC_STATE_PATH.exists():
            with open(TOPIC_STATE_PATH, encoding="utf-8") as f:
                return json.load(f).get("next_index", 0)
    except Exception as exc:
        log.warning("Could not load topic state: %s — starting from 0", exc)
    return 0


def _save_next_topic_index(next_index: int):
    TOPIC_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOPIC_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"next_index": next_index}, f, indent=2)


def _next_kids_topic() -> dict:
    """Pop the next unused kids topic from the fixed pool."""
    try:
        if KIDS_TOPIC_STATE_PATH.exists():
            with open(KIDS_TOPIC_STATE_PATH, encoding="utf-8") as f:
                next_index = json.load(f).get("next_index", 0)
        else:
            next_index = 0
    except Exception as exc:
        log.warning("Could not load kids topic state: %s — starting from 0", exc)
        next_index = 0

    if next_index >= len(KIDS_TOPICS):
        raise RuntimeError(
            f"All {len(KIDS_TOPICS)} kids topics have been used — add more topics "
            f"to kids_topics.KIDS_TOPICS before the pipeline can continue."
        )
    topic = KIDS_TOPICS[next_index]
    KIDS_TOPIC_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(KIDS_TOPIC_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"next_index": next_index + 1}, f, indent=2)
    log.info("Selected kids topic #%d/%d: %s", topic["id"], len(KIDS_TOPICS), topic["title"])
    return topic


def _next_story_topic() -> dict:
    """Pop the next unused topic from the fixed pool. Raises once exhausted."""
    next_index = _load_next_topic_index()
    if next_index >= len(STORY_TOPICS):
        raise RuntimeError(
            f"All {len(STORY_TOPICS)} story topics have been used — add more topics "
            f"to story_topics.STORY_TOPICS before the pipeline can continue."
        )
    topic = STORY_TOPICS[next_index]
    _save_next_topic_index(next_index + 1)
    log.info("Selected topic #%d/%d: %s", topic["id"], len(STORY_TOPICS), topic["title"])
    return topic


# ── animated kids pipeline ───────────────────────────────────────────────────

def _run_animated_kids_pipeline(job_id, job_dir, temp_dir, result, history, slot) -> dict:
    """Animated kids pipeline: storyboard → cartoon images → voiceover → video."""
    try:
        topic = _next_kids_topic()

        log.info("[1] Generating storyboard for '%s'...", topic["title"])
        storyboard = generate_storyboard(topic)
        _save_json(job_dir / "storyboard.json", storyboard)

        log.info("[2] Generating voiceover script from storyboard...")
        script_data = generate_animated_kids_script(storyboard)
        _save_json(job_dir / "script.json", script_data)

        images_dir = temp_dir / "cartoon_images"
        vo_path = temp_dir / "voiceover.mp3"

        log.info("[3] Generating %d cartoon scene images...", len(storyboard["scenes"]))
        image_paths = generate_cartoon_images(storyboard["scenes"], images_dir)
        if not image_paths:
            raise RuntimeError("Cartoon image generation returned no images")

        log.info("[4] Generating voiceover...")
        generate_voiceover(script_data["script"], vo_path)

        log.info("[5] Assembling animated video...")
        raw_path = job_dir / "final_raw.mp4"
        create_animated_kids_video(
            storyboard=storyboard,
            image_paths=image_paths,
            voiceover_path=vo_path,
            output_path=raw_path,
            temp_dir=temp_dir,
        )

        log.info("[5b] Enhancing with FFmpeg...")
        final_path = job_dir / "final.mp4"
        try:
            enhance_video(raw_path, final_path, temp_dir)
        except Exception as exc:
            log.warning("Enhancement failed: %s — using raw", exc)
            shutil.copy2(raw_path, final_path)

        log.info("[6] Generating SEO metadata...")
        seo_data = generate_animated_kids_seo(
            topic=script_data["topic"],
            hook=script_data["hook"],
        )
        _save_json(job_dir / "seo.json", seo_data)

        log.info("[6b] Generating thumbnail...")
        thumb_path = job_dir / "thumbnail.jpg"
        try:
            create_thumbnail(
                title=seo_data["title"],
                hook=script_data["hook"],
                image_paths=image_paths,
                output_path=thumb_path,
            )
        except Exception as exc:
            log.warning("Thumbnail failed: %s — continuing without", exc)
            thumb_path = None

        log.info("[7] Uploading to YouTube...")
        video_id = upload_video(
            video_path=final_path,
            title=seo_data["title"],
            description=seo_data["description"],
            tags=seo_data["tags"],
            hashtags=seo_data["hashtags"],
            category_id="27",  # Education
        )

        if thumb_path and thumb_path.exists():
            log.info("[7b] Uploading thumbnail...")
            upload_thumbnail(video_id, thumb_path)

        _update_history(history, seo_data["title"], script_data["topic"])

        result.update({
            "status":   "success",
            "video_id": video_id,
            "url":      f"https://www.youtube.com/watch?v={video_id}",
            "title":    seo_data["title"],
            "source":   script_data["topic"],
            "topic_id": topic["id"],
            "category": topic["category"],
            "scenes":   len(storyboard["scenes"]),
        })
        _save_json(job_dir / "result.json", result)

        log.info("=" * 60)
        log.info("SUCCESS (animated kids): %s", result["url"])
        log.info("=" * 60)

    except Exception as exc:
        result["error"] = str(exc)
        _save_json(job_dir / "result.json", result)
        log.error("ANIMATED KIDS JOB FAILED (%s): %s", job_id, exc, exc_info=True)

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    return result


# ── kids pipeline ─────────────────────────────────────────────────────────────

def _run_kids_pipeline(job_id, job_dir, temp_dir, result, history, slot) -> dict:
    """Children's educational pipeline using Google Veo 2 AI video clips."""
    try:
        topic = _next_kids_topic()

        log.info("[1] Generating kids script for '%s'...", topic["title"])
        script_data = generate_kids_script(topic)
        _save_json(job_dir / "script.json", script_data)

        clips_dir = temp_dir / "veo_clips"
        vo_path = temp_dir / "voiceover.mp3"

        log.info("[2] Generating Veo 2 video clips...")
        clip_paths = generate_veo_clips(
            topic=script_data["topic"],
            keywords=script_data["keywords"],
            output_dir=clips_dir,
        )
        if not clip_paths:
            raise RuntimeError("Veo 2 clip generation returned no clips")

        log.info("[3] Generating voiceover...")
        generate_voiceover(script_data["script"], vo_path)

        log.info("[4] Assembling kids video from Veo clips...")
        raw_path = job_dir / "final_raw.mp4"
        create_veo_video(
            topic=script_data["topic"],
            clip_paths=clip_paths,
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

        log.info("[5] Generating kids SEO metadata...")
        seo_data = generate_kids_seo(
            topic=script_data["topic"],
            hook=script_data["hook"],
        )
        _save_json(job_dir / "seo.json", seo_data)
        log.info("Title: %s", seo_data["title"])

        log.info("[5b] Generating thumbnail...")
        thumb_path = job_dir / "thumbnail.jpg"
        try:
            # Use first frame from first clip as background for thumbnail
            from agents.thumbnail_agent import create_thumbnail as _create_thumb
            _create_thumb(
                title=seo_data["title"],
                hook=script_data["hook"],
                image_paths=[],
                output_path=thumb_path,
            )
        except Exception as exc:
            log.warning("Thumbnail generation failed: %s — continuing without", exc)
            thumb_path = None

        log.info("[6] Uploading to YouTube...")
        video_id = upload_video(
            video_path=final_path,
            title=seo_data["title"],
            description=seo_data["description"],
            tags=seo_data["tags"],
            hashtags=seo_data["hashtags"],
            category_id="27",  # 27 = Education
        )

        if thumb_path and thumb_path.exists():
            log.info("[6b] Uploading thumbnail...")
            upload_thumbnail(video_id, thumb_path)

        _update_history(history, seo_data["title"], script_data["topic"])

        result.update({
            "status":   "success",
            "video_id": video_id,
            "url":      f"https://www.youtube.com/watch?v={video_id}",
            "title":    seo_data["title"],
            "source":   script_data["topic"],
            "topic_id": topic["id"],
            "category": topic["category"],
        })
        _save_json(job_dir / "result.json", result)

        log.info("=" * 60)
        log.info("SUCCESS (kids): %s", result["url"])
        log.info("=" * 60)

    except Exception as exc:
        result["error"] = str(exc)
        _save_json(job_dir / "result.json", result)
        log.error("KIDS JOB FAILED (%s): %s", job_id, exc, exc_info=True)

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    return result


# ── main pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(slot: int = 0) -> dict:
    """Run one full pipeline for the next story topic in the queue."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    job_id    = f"{timestamp}_slot{slot}"
    job_dir   = OUTPUT_DIR / job_id
    temp_dir  = job_dir / "temp"
    job_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("STARTING JOB: %s", job_id)
    log.info("=" * 60)

    result  = {"job_id": job_id, "status": "failed", "content_type": CONTENT_TYPE}
    history = _load_history()

    try:
        if CONTENT_TYPE == "animated_kids":
            return _run_animated_kids_pipeline(job_id, job_dir, temp_dir, result, history, slot)
        if CONTENT_TYPE == "kids":
            return _run_kids_pipeline(job_id, job_dir, temp_dir, result, history, slot)

        topic = _next_story_topic()

        log.info("[1] Generating story script for '%s'...", topic["title"])
        script_data = generate_story_script(topic, used_titles=history.get("titles", []))
        _save_json(job_dir / "script.json", script_data)

        images_dir = temp_dir / "images"
        vo_path = temp_dir / "voiceover.mp3"

        log.info("[2] Generating images...")
        images = generate_images(
            topic=script_data["topic"],
            keywords=script_data["keywords"],
            output_dir=images_dir,
        )
        if not images:
            raise RuntimeError("Image generation returned no images")

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
            niche="story",
            used_titles=history.get("titles", []),
        )
        _save_json(job_dir / "seo.json", seo_data)
        log.info("Title: %s", seo_data["title"])

        log.info("[5b] Generating thumbnail...")
        thumb_path = job_dir / "thumbnail.jpg"
        try:
            create_thumbnail(
                title=seo_data["title"],
                hook=script_data["hook"],
                image_paths=images,
                output_path=thumb_path,
            )
        except Exception as exc:
            log.warning("Thumbnail generation failed: %s — continuing without", exc)
            thumb_path = None

        log.info("[6] Uploading to YouTube...")
        video_id = upload_video(
            video_path=final_path,
            title=seo_data["title"],
            description=seo_data["description"],
            tags=seo_data["tags"],
            hashtags=seo_data["hashtags"],
            category_id=YOUTUBE_CATEGORY_ID,
        )

        if thumb_path and thumb_path.exists():
            log.info("[6b] Uploading thumbnail...")
            upload_thumbnail(video_id, thumb_path)

        _update_history(history, seo_data["title"], script_data["topic"])

        result.update({
            "status":   "success",
            "video_id": video_id,
            "url":      f"https://www.youtube.com/watch?v={video_id}",
            "title":    seo_data["title"],
            "source":   script_data["topic"],
            "topic_id": topic["id"],
            "category": topic["category"],
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
    if len(POSTING_TIMES) < 4:
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
    parser = argparse.ArgumentParser(description="YouTube Story Video Bot")
    parser.add_argument("--run-now", action="store_true",
                        help="Run one video immediately and exit")
    parser.add_argument("--slot", type=int, default=0, choices=[0, 1, 2, 3],
                        help="Slot to run (0=night, 1=morning, 2=afternoon, 3=evening)")
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
