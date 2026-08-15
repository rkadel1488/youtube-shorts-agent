"""
Assembles the final YouTube video from stock images + voiceover:
  1. Ken Burns zoom/pan effect alternating per image
  2. Title card + on-screen hook caption overlays
  3. Mux voiceover audio
  4. Export 1920x1080 landscape MP4

Compatible with MoviePy 2.x (with_duration/with_position/etc.)
"""
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)

from config import VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
from utils.logger import get_logger

log = get_logger(__name__)

TITLE_FONT_SIZE = 48
TITLE_Y_RATIO   = 0.04
TITLE_PADDING   = 16

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
    """Dark banner at the top showing the story title for the first 6 seconds."""
    font    = _load_font(TITLE_FONT_SIZE)
    wrapped = textwrap.fill(text[:80], width=50)
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
                           radius=12, fill=(20, 20, 20, 210))
    y_cur = TITLE_PADDING * 2
    for line, bbox in zip(lines, bboxes):
        lx = (VIDEO_WIDTH - (bbox[2] - bbox[0])) // 2
        draw.text((lx + 2, y_cur + 2), line, font=font, fill=(0, 0, 0, 160))
        draw.text((lx,     y_cur),     line, font=font, fill=(255, 255, 255, 255))
        y_cur += line_h + TITLE_PADDING

    return (
        ImageClip(np.array(img))
        .with_start(0)
        .with_duration(min(6.0, duration))
        .with_position(("center", int(VIDEO_HEIGHT * TITLE_Y_RATIO)))
    )


def _hook_overlay(text: str, duration: float) -> ImageClip:
    """Large centred text overlay for the opening hook — visible to silent viewers."""
    font_size = 64
    font = _load_font(font_size)
    wrapped = textwrap.fill(text[:60], width=30)
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
    draw.rectangle([0, pad, img_w, img_h - pad], fill=(0, 0, 0, 180))
    y_cur = pad * 2
    for line, bbox in zip(lines, bboxes):
        lw = bbox[2] - bbox[0]
        lx = (img_w - lw) // 2
        draw.text((lx + 3, y_cur + 3), line, font=font, fill=(0, 0, 0, 200))
        draw.text((lx, y_cur), line, font=font, fill=(255, 255, 255, 255))
        y_cur += line_h + pad

    y_pos = int(VIDEO_HEIGHT * 0.42) - img_h // 2
    return (
        ImageClip(np.array(img))
        .with_start(0)
        .with_duration(min(4.0, duration))
        .with_position(("center", max(0, y_pos)))
    )


# ── Veo kids video assembler ─────────────────────────────────────────────────

def create_veo_video(
    topic: str,
    clip_paths: list,
    voiceover_path: Path,
    output_path: Path,
    temp_dir: Path,
    on_screen_hook: str | None = None,
) -> Path:
    """
    Stitch Veo 2 mp4 clips together to fill the voiceover duration,
    mux voiceover audio, add title + hook overlays.
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not clip_paths:
        raise RuntimeError("No Veo clips provided for video assembly")

    voiceover = AudioFileClip(str(voiceover_path))
    total_duration = max(voiceover.duration, 20.0)

    raw_clips = [VideoFileClip(str(p)) for p in clip_paths]
    looped = []
    accumulated = 0.0
    i = 0
    while accumulated < total_duration:
        clip = raw_clips[i % len(raw_clips)]
        remaining = total_duration - accumulated
        if clip.duration > remaining:
            clip = clip.subclipped(0, remaining)
        looped.append(clip)
        accumulated += clip.duration
        i += 1

    video = concatenate_videoclips(looped, method="compose")
    if video.duration > total_duration:
        video = video.subclipped(0, total_duration)

    video = video.with_audio(voiceover)

    title_clip = _title_overlay(topic, min(6.0, total_duration))
    layers = [video, title_clip]
    if on_screen_hook:
        layers.append(_hook_overlay(on_screen_hook, total_duration))
    final = CompositeVideoClip(layers, size=(video.w, video.h))

    log.info("Rendering Veo video -> %s", output_path)
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
    for c in raw_clips:
        c.close()

    log.info("Veo video done: %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)
    return output_path


# ── animated kids video assembler ────────────────────────────────────────────

def _kids_caption_overlay(text: str, start: float, duration: float,
                           color: tuple = (255, 220, 0)) -> ImageClip:
    """Large colourful caption bar at the bottom for kids — word-wrapped, bold."""
    font_size = 72
    font = _load_font(font_size)
    wrapped = textwrap.fill(text, width=28)
    lines = wrapped.split("\n")

    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bboxes = [draw.textbbox((0, 0), l, font=font) for l in lines]
    line_h = max(b[3] - b[1] for b in bboxes) if bboxes else font_size
    pad = 28
    img_h = line_h * len(lines) + pad * (len(lines) + 1)
    img_w = VIDEO_WIDTH

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Rounded dark background pill
    draw.rectangle([0, 0, img_w, img_h], fill=(20, 20, 20, 210))
    y_cur = pad
    for line, bbox in zip(lines, bboxes):
        lw = bbox[2] - bbox[0]
        lx = (img_w - lw) // 2
        # Shadow
        draw.text((lx + 3, y_cur + 3), line, font=font, fill=(0, 0, 0, 200))
        # Main colourful text
        draw.text((lx, y_cur), line, font=font, fill=color + (255,))
        y_cur += line_h + pad

    y_pos = VIDEO_HEIGHT - img_h - 24
    return (
        ImageClip(np.array(img))
        .with_start(start)
        .with_duration(duration)
        .with_position(("center", y_pos))
    )


def create_animated_kids_video(
    storyboard: dict,
    image_paths: list[Path],
    voiceover_path: Path,
    output_path: Path,
    temp_dir: Path,
) -> Path:
    """
    Assemble animated kids video:
    - One image per storyboard scene with Ken Burns zoom
    - Colourful caption overlay per scene (narration text)
    - Voiceover audio muxed in
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scenes = storyboard.get("scenes", [])
    if not image_paths:
        raise RuntimeError("No cartoon images provided for animated video assembly")

    voiceover = AudioFileClip(str(voiceover_path))
    total_duration = max(voiceover.duration, 20.0)

    # Distribute time evenly across scenes we have images for
    n = min(len(image_paths), len(scenes))
    if n == 0:
        raise RuntimeError("No scenes with images to assemble")
    seg_duration = total_duration / n

    # Rotating caption colours for visual variety
    caption_colors = [
        (255, 220, 0),   # yellow
        (100, 220, 255), # sky blue
        (180, 255, 100), # lime green
        (255, 160, 80),  # orange
        (220, 140, 255), # purple
        (255, 120, 160), # pink
        (80, 255, 200),  # mint
    ]

    clips = []
    caption_layers = []

    for i in range(n):
        img_path = image_paths[i]
        img = Image.open(img_path).convert("RGB").resize(
            (VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS
        )
        arr = np.array(img)

        zoom_in = (i % 2 == 0)
        s, e = (1.0, 1.06) if zoom_in else (1.06, 1.0)

        clip = (
            ImageClip(arr)
            .with_duration(seg_duration)
            .resized(lambda t, s=s, e=e, d=seg_duration: s + (e - s) * (t / d))
            .cropped(x_center=VIDEO_WIDTH // 2, y_center=VIDEO_HEIGHT // 2,
                     width=VIDEO_WIDTH, height=VIDEO_HEIGHT)
            .resized((VIDEO_WIDTH, VIDEO_HEIGHT))
        )
        clips.append(clip)

        # Caption from storyboard narration
        if i < len(scenes):
            narration = scenes[i].get("narration", "")
            if narration:
                color = caption_colors[i % len(caption_colors)]
                start_t = i * seg_duration
                caption_layers.append(
                    _kids_caption_overlay(narration, start_t, seg_duration, color)
                )

    video = concatenate_videoclips(clips, method="compose")
    if video.duration > total_duration:
        video = video.subclipped(0, total_duration)
    video = video.with_audio(voiceover)

    # Title overlay for first 5 seconds
    title_clip = _title_overlay(storyboard.get("title", ""), min(5.0, total_duration))
    layers = [video, title_clip] + caption_layers
    final = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))

    log.info("Rendering animated kids video -> %s", output_path)
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

    log.info("Animated kids video done: %s (%.1f MB)",
             output_path, output_path.stat().st_size / 1e6)
    return output_path


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
    Assemble a landscape YouTube video from stock images + voiceover.
    Applies Ken Burns zoom effect to each image, muxes voiceover audio.
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not image_paths:
        raise RuntimeError("No images provided for video assembly")

    voiceover = AudioFileClip(str(voiceover_path))
    total_duration = max(voiceover.duration, 20.0)
    seg_duration = total_duration / len(image_paths)
    clips = []

    for i, img_path in enumerate(image_paths):
        img = Image.open(img_path).convert("RGB").resize(
            (VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS
        )
        arr = np.array(img)

        zoom_in = (i % 2 == 0)
        start_scale = 1.0 if zoom_in else 1.08
        end_scale = 1.08 if zoom_in else 1.0

        def _make_zoom(s, e, d):
            return lambda t: s + (e - s) * (t / d)

        clip = (
            ImageClip(arr)
            .with_duration(seg_duration)
            .resized(_make_zoom(start_scale, end_scale, seg_duration))
            .cropped(x_center=VIDEO_WIDTH // 2, y_center=VIDEO_HEIGHT // 2,
                     width=VIDEO_WIDTH, height=VIDEO_HEIGHT)
            .resized((VIDEO_WIDTH, VIDEO_HEIGHT))
        )
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")
    if video.duration > total_duration:
        video = video.subclipped(0, total_duration)

    video = video.with_audio(voiceover)

    title = _title_overlay(topic, min(6.0, total_duration))
    layers = [video, title]
    if on_screen_hook:
        layers.append(_hook_overlay(on_screen_hook, total_duration))
    final = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))

    log.info("Rendering video -> %s", output_path)
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

    log.info("Video done: %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)
    return output_path
