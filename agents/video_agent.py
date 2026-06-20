"""
Assembles the final YouTube Short from AI-generated images + voiceover:
  1. Ken Burns zoom/pan effect alternating per image
  2. Title card + on-screen hook caption overlays
  3. Mux voiceover audio
  4. Export 1080x1920 MP4
"""
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
)

from config import VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
from utils.logger import get_logger

log = get_logger(__name__)

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


def _hook_overlay(text: str, duration: float) -> ImageClip:
    """Large centred text overlay for the opening hook — visible to silent viewers."""
    font_size = 72
    font = _load_font(font_size)
    wrapped = textwrap.fill(text[:50], width=14)
    lines = wrapped.split("\n")

    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bboxes = [draw.textbbox((0, 0), l, font=font) for l in lines]
    line_h = max(b[3] - b[1] for b in bboxes) if bboxes else font_size
    pad = 24
    total_h = line_h * len(lines) + pad * (len(lines) - 1) + pad * 2
    img_w = VIDEO_WIDTH
    img_h = total_h + pad * 2

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Semi-transparent black background strip
    draw.rectangle([0, pad, img_w, img_h - pad], fill=(0, 0, 0, 180))
    y_cur = pad * 2
    for line, bbox in zip(lines, bboxes):
        lw = bbox[2] - bbox[0]
        lx = (img_w - lw) // 2
        # Shadow
        draw.text((lx + 3, y_cur + 3), line, font=font, fill=(0, 0, 0, 200))
        # White text
        draw.text((lx, y_cur), line, font=font, fill=(255, 255, 255, 255))
        y_cur += line_h + pad

    y_pos = int(VIDEO_HEIGHT * 0.38) - img_h // 2
    return (
        ImageClip(np.array(img), ismask=False)
        .set_start(0)
        .set_duration(min(3.5, duration))
        .set_position(("center", max(0, y_pos)))
    )


# ── main entry ───────────────────────────────────────────────────────────────

def create_ai_video(
    topic: str,
    image_paths: list,
    voiceover_path: Path,
    output_path: Path,
    temp_dir: Path,
    on_screen_hook: str | None = None,
) -> Path:
    """
    Assemble a YouTube Short from AI-generated images + voiceover.
    Applies Ken Burns zoom effect to each image, muxes voiceover audio.
    """
    from moviepy.editor import concatenate_videoclips

    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not image_paths:
        raise RuntimeError("No images provided for AI video")

    voiceover = AudioFileClip(str(voiceover_path))
    total_duration = max(voiceover.duration, 10.0)
    seg_duration = total_duration / len(image_paths)
    clips = []

    for i, img_path in enumerate(image_paths):
        img = Image.open(img_path).convert("RGB").resize(
            (VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS
        )
        arr = np.array(img)

        zoom_in = (i % 2 == 0)
        start_scale = 1.0 if zoom_in else 1.12
        end_scale = 1.12 if zoom_in else 1.0

        def _make_zoom(s, e, d):
            return lambda t: s + (e - s) * (t / d)

        clip = (
            ImageClip(arr)
            .set_duration(seg_duration)
            .resize(_make_zoom(start_scale, end_scale, seg_duration))
            .crop(x_center=VIDEO_WIDTH // 2, y_center=VIDEO_HEIGHT // 2,
                  width=VIDEO_WIDTH, height=VIDEO_HEIGHT)
            .resize((VIDEO_WIDTH, VIDEO_HEIGHT))
        )
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")
    if video.duration > total_duration:
        video = video.subclip(0, total_duration)

    video = video.set_audio(voiceover)

    title = _title_overlay(topic, min(6.0, total_duration))
    layers = [video, title]
    if on_screen_hook:
        layers.append(_hook_overlay(on_screen_hook, total_duration))
    final = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))

    log.info("Rendering AI video -> %s", output_path)
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

    final.close()
    video.close()
    for c in clips:
        c.close()

    log.info("AI video done: %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)
    return output_path
