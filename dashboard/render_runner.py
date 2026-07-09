"""
Two ways to get a vertical Short, both just producing a downloadable file —
nothing auto-posts anywhere:

  1. From a YouTube link: transcript -> Claude picks the best 30-60s moment
     -> cut + reframe to vertical.
  2. From an uploaded video: you specify the start/end seconds yourself
     (no transcript available for an arbitrary upload) -> cut + reframe.
"""
import os
import shutil
import traceback
from pathlib import Path

import db
from clipper import clip_youtube_video, cut_and_reframe
from utils.logger import get_logger

log = get_logger(__name__)

# Must live on the same persistent volume as the DB, or finished renders
# vanish on every redeploy (same class of bug that wiped accounts earlier).
WORK_DIR = Path(os.getenv("RENDERS_DIR", str(Path(__file__).parent / "renders")))
WORK_DIR.mkdir(parents=True, exist_ok=True)


def render_from_youtube(youtube_url: str) -> dict:
    render_id = db.create_render("youtube", source=youtube_url)
    job_dir = WORK_DIR / f"render_{render_id}"
    try:
        log.info("[%d] Clipping from YouTube: %s", render_id, youtube_url)
        clip = clip_youtube_video(youtube_url, job_dir)

        final_path = WORK_DIR / f"render_{render_id}.mp4"
        shutil.copy2(clip["video_path"], final_path)

        db.finish_render(render_id, "success", output_path=str(final_path),
                         hook_title=clip["hook_title"])
        log.info("[%d] Done: %s", render_id, clip["hook_title"])
        return {"render_id": render_id, "status": "success", "hook_title": clip["hook_title"]}

    except Exception:
        tb = traceback.format_exc()
        log.error("[%d] Failed:\n%s", render_id, tb)
        db.finish_render(render_id, "failed", error=tb)
        return {"render_id": render_id, "status": "failed", "error": tb}
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)  # keep only the final mp4, not source/work files


def render_from_upload(uploaded_path: Path, original_filename: str,
                       start_seconds: float, end_seconds: float) -> dict:
    render_id = db.create_render("upload", source=original_filename)
    try:
        log.info("[%d] Reframing uploaded video %s (%.1fs-%.1fs)",
                render_id, original_filename, start_seconds, end_seconds)
        final_path = WORK_DIR / f"render_{render_id}.mp4"
        cut_and_reframe(uploaded_path, start_seconds, end_seconds, final_path)

        db.finish_render(render_id, "success", output_path=str(final_path))
        log.info("[%d] Done", render_id)
        return {"render_id": render_id, "status": "success"}

    except Exception:
        tb = traceback.format_exc()
        log.error("[%d] Failed:\n%s", render_id, tb)
        db.finish_render(render_id, "failed", error=tb)
        return {"render_id": render_id, "status": "failed", "error": tb}
    finally:
        uploaded_path.unlink(missing_ok=True)  # don't keep the raw upload around
