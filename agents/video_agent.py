"""
Assembles the final YouTube Short from:
  - A downloaded CC-licensed cricket Short (real match footage)
  - A free background music track (NCS / FreePD)

Steps:
  1. Crop video to 1080x1920 portrait if needed
  2. Trim to SHORT_DURATION seconds
  3. Strip original audio, replace with music at low volume
  4. Add a match title card at the top (first 6 seconds)
  5. Export MP4
"""
import subprocess
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_audioclips,
    concatenate_videoclips,
)

from agents.music_agent import download_music
from agents.yt_shorts_agent import download_cc_cricket_short
from config import VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
from utils.logger import get_logger

log = get_logger(__name__)

SHORT_DURATION  = 28      # seconds — ideal for Shorts completion rate
MUSIC_VOLUME    = 0.18    # background volume (0 = silent, 1 = full)

TITLE_FONT_SIZE = 50
TITLE_Y_RATIO   = 0.04
TITLE_PADDING   = 18

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


# ── helpers ──────────────────────────────────────────────────────────────────

def _load_font(size: int):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _title_overlay(text: str, duration: float) -> ImageClip:
    """Red banner at the top showing the match title for the first 6 seconds."""
    font    = _load_font(TITLE_FONT_SIZE)
    wrapped = textwrap.fill(text[:60], width=28)
    lines   = wrapped.split("\n")

    dummy  = Image.new("RGBA", (1, 1))
    draw   = ImageDraw.Draw(dummy)
    bboxes = [draw.textbbox((0, 0), l, font=font) for l in lines]
    text_w = max(b[2] - b[0] for b in bboxes)
    line_h = max(b[3] - b[1] for b in bboxes)
    total_h = line_h * len(lines) + TITLE_PADDING * (len(lines) - 1)
    box_w  = text_w + TITLE_PADDING * 4
    box_h  = total_h + TITLE_PADDING * 2

    img  = Image.new("RGBA", (VIDEO_WIDTH, box_h + TITLE_PADDING * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    x0   = (VIDEO_WIDTH - box_w) // 2
    draw.rounded_rectangle([x0, TITLE_PADDING, x0 + box_w, TITLE_PADDING + box_h],
                           radius=14, fill=(190, 0, 0, 220))
    y_cur = TITLE_PADDING * 2
    for line, bbox in zip(lines, bboxes):
        lx = (VIDEO_WIDTH - (bbox[2] - bbox[0])) // 2
        draw.text((lx + 2, y_cur + 2), line, font=font, fill=(0, 0, 0, 160))
        draw.text((lx,     y_cur),     line, font=font, fill=(255, 255, 255, 255))
        y_cur += line_h + TITLE_PADDING

    return (
        ImageClip(np.array(img), ismask=False)
        .set_start(0)
        .set_duration(min(6.0, duration))
        .set_position(("center", int(VIDEO_HEIGHT * TITLE_Y_RATIO)))
    )


def _crop_portrait(clip: VideoFileClip) -> VideoFileClip:
    """Center-crop to 1080×1920 portrait."""
    ratio = VIDEO_WIDTH / VIDEO_HEIGHT
    if clip.w / clip.h > ratio:
        scale = VIDEO_HEIGHT / clip.h
        clip  = clip.resize((int(clip.w * scale), VIDEO_HEIGHT))
        x1    = (clip.w - VIDEO_WIDTH) // 2
        clip  = clip.crop(x1=x1, x2=x1 + VIDEO_WIDTH)
    else:
        scale = VIDEO_WIDTH / clip.w
        clip  = clip.resize((VIDEO_WIDTH, int(clip.h * scale)))
        y1    = (clip.h - VIDEO_HEIGHT) // 2
        clip  = clip.crop(y1=y1, y2=y1 + VIDEO_HEIGHT)
    return clip.resize((VIDEO_WIDTH, VIDEO_HEIGHT))


# ── main entry ───────────────────────────────────────────────────────────────

def create_video(
    topic: str,
    output_path: Path,
    temp_dir: Path,
    cc_path: Path | None = None,
    **_kwargs,
) -> Path:
    """
    Assemble final Short from a CC cricket video + background music.
    cc_path: already-downloaded CC Short (passed from main to avoid double download).
    Returns *output_path*.
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Use the provided CC path (already downloaded by main.py)
    if not cc_path or not cc_path.exists():
        log.info("cc_path not provided — downloading now...")
        cc_path, video_info = download_cc_cricket_short(temp_dir)
        topic = video_info.get("title", topic) or topic

    if not cc_path or not cc_path.exists():
        raise RuntimeError("No CC cricket Short available to build video from.")

    # 2. Load, crop to portrait, trim to SHORT_DURATION
    raw     = VideoFileClip(str(cc_path), audio=False)
    base    = _crop_portrait(raw)
    if base.duration > SHORT_DURATION:
        base = base.subclip(0, SHORT_DURATION)
    elif base.duration < 5:
        raise RuntimeError(f"Downloaded video too short: {base.duration:.1f}s")

    duration = base.duration
    log.info("Base video: %.1fs @ %dx%d", duration, base.w, base.h)

    # 3. Download background music
    log.info("Downloading background music...")
    music_path = download_music(temp_dir / "music.mp3")
    if music_path and music_path.exists():
        try:
            music = AudioFileClip(str(music_path))
            if music.duration < duration:
                loops = int(duration / music.duration) + 1
                music = concatenate_audioclips([music] * loops)
            music = music.subclip(0, duration).volumex(MUSIC_VOLUME)
            base  = base.set_audio(music)
            log.info("Music added at %.0f%% volume", MUSIC_VOLUME * 100)
        except Exception as exc:
            log.warning("Could not add music: %s", exc)
    else:
        log.warning("No music available — video will be silent")

    # 4. Add title card overlay
    title = _title_overlay(topic, duration)
    final = CompositeVideoClip([base, title], size=(VIDEO_WIDTH, VIDEO_HEIGHT))

    # 5. Export
    log.info("Rendering final video -> %s", output_path)
    final.write_videofile(
        str(output_path),
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=str(temp_dir / "tmp_audio.m4a"),
        remove_temp=True,
        logger=None,
        threads=4,
        preset="fast",
    )

    raw.close()
    base.close()
    final.close()

    log.info("Done: %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)
    return output_path
