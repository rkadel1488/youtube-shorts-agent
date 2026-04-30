"""
Creates a 1080×1920 YouTube Short from:
  - Stock video clips (Pexels)
  - An MP3 voiceover
  - Auto-generated caption overlays (Pillow, no ImageMagick needed)

Pipeline:
  1. Download clips from Pexels
  2. Crop/resize each clip to 1080×1920
  3. Concatenate clips to match audio length
  4. Render caption overlay images with Pillow
  5. Composite captions onto video
  6. Mux in voiceover audio
  7. Export final MP4
"""
import math
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image

# MoviePy 1.0.3 uses Image.ANTIALIAS which was removed in Pillow 10+
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)

from config import VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
from utils.logger import get_logger
from utils.pexels_client import fetch_clips

log = get_logger(__name__)

# ── Caption styling ────────────────────────────────────────────────────────────
CAPTION_FONT_SIZE = 68
CAPTION_MAX_CHARS = 28      # chars per line before wrapping
CAPTION_Y_RATIO = 0.72      # vertical position (fraction of frame height)
CAPTION_PADDING = 22
CAPTION_BG_ALPHA = 180      # 0-255 transparency of background box
CAPTION_WORDS_PER_CHUNK = 4

# System font candidates (Windows -> Linux fallback)
FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _make_caption_frame(text: str, width: int, font) -> np.ndarray:
    """Render *text* as an RGBA numpy array (caption overlay)."""
    wrapped = textwrap.fill(text, width=CAPTION_MAX_CHARS)
    lines = wrapped.split("\n")

    # Measure text size
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    line_bboxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    text_w = max(bb[2] - bb[0] for bb in line_bboxes)
    line_h = max(bb[3] - bb[1] for bb in line_bboxes)
    total_h = line_h * len(lines) + CAPTION_PADDING * (len(lines) - 1)

    box_w = text_w + CAPTION_PADDING * 4
    box_h = total_h + CAPTION_PADDING * 2

    img = Image.new("RGBA", (width, box_h + CAPTION_PADDING * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    x0 = (width - box_w) // 2
    y0 = CAPTION_PADDING
    draw.rounded_rectangle(
        [x0, y0, x0 + box_w, y0 + box_h],
        radius=16,
        fill=(0, 0, 0, CAPTION_BG_ALPHA),
    )

    y_cursor = y0 + CAPTION_PADDING
    for line, bbox in zip(lines, line_bboxes):
        lw = bbox[2] - bbox[0]
        lx = (width - lw) // 2
        # Shadow
        draw.text((lx + 2, y_cursor + 2), line, font=font, fill=(0, 0, 0, 200))
        # Main text
        draw.text((lx, y_cursor), line, font=font, fill=(255, 255, 255, 255))
        y_cursor += line_h + CAPTION_PADDING

    return np.array(img)


def _to_vertical(clip: VideoFileClip) -> VideoFileClip:
    """Crop and resize a landscape clip to 1080×1920."""
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT  # ~0.5625
    clip_ratio = clip.w / clip.h

    if clip_ratio > target_ratio:
        # Wider than target: scale height to 1920, crop width
        new_h = VIDEO_HEIGHT
        new_w = int(clip.w * VIDEO_HEIGHT / clip.h)
        clip = clip.resize((new_w, new_h))
        x1 = (new_w - VIDEO_WIDTH) // 2
        clip = clip.crop(x1=x1, y1=0, x2=x1 + VIDEO_WIDTH, y2=VIDEO_HEIGHT)
    else:
        # Taller than target: scale width to 1080, crop height
        new_w = VIDEO_WIDTH
        new_h = int(clip.h * VIDEO_WIDTH / clip.w)
        clip = clip.resize((new_w, new_h))
        y1 = (new_h - VIDEO_HEIGHT) // 2
        clip = clip.crop(x1=0, y1=y1, x2=VIDEO_WIDTH, y2=y1 + VIDEO_HEIGHT)

    return clip


def _build_base_video(clip_paths: list[Path], target_duration: float) -> CompositeVideoClip:
    """Concatenate and loop clips to reach *target_duration*."""
    processed = []
    for path in clip_paths:
        try:
            c = VideoFileClip(str(path)).without_audio()
            c = _to_vertical(c)
            processed.append(c)
        except Exception as exc:
            log.warning("Skipping clip %s: %s", path, exc)

    if not processed:
        log.warning("No valid clips — using black fallback")
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=target_duration)

    # Loop until we have enough footage
    total = sum(c.duration for c in processed)
    while total < target_duration + 1:
        processed.extend(processed[:])
        total = sum(c.duration for c in processed)

    base = concatenate_videoclips(processed, method="compose")

    if base.duration > target_duration:
        base = base.subclip(0, target_duration)

    return base


def _build_captions(script: str, total_duration: float) -> list[ImageClip]:
    """Split script into chunks and create timed ImageClips for each."""
    words = script.split()
    chunks = [
        " ".join(words[i: i + CAPTION_WORDS_PER_CHUNK])
        for i in range(0, len(words), CAPTION_WORDS_PER_CHUNK)
    ]
    if not chunks:
        return []

    chunk_duration = total_duration / len(chunks)
    font = _load_font(CAPTION_FONT_SIZE)
    caption_clips = []
    y_pos = int(VIDEO_HEIGHT * CAPTION_Y_RATIO)

    for idx, chunk in enumerate(chunks):
        frame = _make_caption_frame(chunk, VIDEO_WIDTH, font)
        clip = (
            ImageClip(frame, ismask=False)
            .set_start(idx * chunk_duration)
            .set_duration(chunk_duration)
            .set_position(("center", y_pos))
        )
        caption_clips.append(clip)

    return caption_clips


def create_video(
    script: str,
    audio_path: Path,
    keywords: list[str],
    output_path: Path,
    temp_dir: Path,
) -> Path:
    """
    Full pipeline: download clips -> build base video -> add captions -> mux audio -> export.
    Returns *output_path*.
    """
    log.info("Starting video creation…")

    # 1. Load audio to get exact duration
    audio = AudioFileClip(str(audio_path))
    duration = audio.duration
    log.info("Audio duration: %.2fs", duration)

    # 2. Download stock clips from Pexels
    clips_dir = temp_dir / "clips"
    clip_paths = fetch_clips(keywords, count=6, dest_dir=clips_dir)

    # 3. Build base video
    base = _build_base_video(clip_paths, duration)

    # 4. Build caption overlays
    captions = _build_captions(script, duration)

    # 5. Composite
    layers = [base] + captions
    final = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))

    # 6. Attach audio
    final = final.set_audio(audio)

    # 7. Export
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log.info("Rendering video -> %s", output_path)
    final.write_videofile(
        str(output_path),
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=str(temp_dir / "temp_audio.m4a"),
        remove_temp=True,
        logger=None,  # suppress moviepy's own progress bar
        threads=4,
        preset="fast",
    )

    # Clean up in-memory clips
    audio.close()
    base.close()
    final.close()

    log.info("Video ready: %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)
    return output_path
