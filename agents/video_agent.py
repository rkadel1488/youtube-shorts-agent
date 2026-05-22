"""
Creates a 1080x1920 YouTube Short from:
  - Copyright-free stock video clips (Pexels) cropped to portrait
  - An MP3 voiceover
  - Auto-generated caption overlays (Pillow — no ImageMagick needed)

Pipeline:
  1. Fetch stock video clips from Pexels
  2. Crop / resize each clip to 1080x1920 portrait
  3. Concatenate clips to match audio length (loop if needed)
  4. Render caption overlays with Pillow
  5. Composite captions onto video
  6. Mux in voiceover audio
  7. Export final MP4
"""
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# MoviePy 1.0.3 uses Image.ANTIALIAS which was removed in Pillow 10+
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)

from agents.video_clip_agent import fetch_clips
from config import VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
from utils.logger import get_logger

log = get_logger(__name__)

# ── Caption styling ──────────────────────────────────────────────────────────
CAPTION_FONT_SIZE = 68
CAPTION_MAX_CHARS = 28
CAPTION_Y_RATIO = 0.74
CAPTION_PADDING = 22
CAPTION_BG_ALPHA = 185
CAPTION_WORDS_PER_CHUNK = 4

FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _load_font(size: int):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


# ── Caption rendering ────────────────────────────────────────────────────────

def _make_caption_frame(text: str, width: int, font) -> np.ndarray:
    """Render *text* as an RGBA numpy array for use as a caption overlay."""
    wrapped = textwrap.fill(text, width=CAPTION_MAX_CHARS)
    lines = wrapped.split("\n")

    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bboxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    text_w = max(bb[2] - bb[0] for bb in bboxes)
    line_h = max(bb[3] - bb[1] for bb in bboxes)
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
    for line, bbox in zip(lines, bboxes):
        lw = bbox[2] - bbox[0]
        lx = (width - lw) // 2
        draw.text((lx + 2, y_cursor + 2), line, font=font, fill=(0, 0, 0, 200))
        draw.text((lx, y_cursor), line, font=font, fill=(255, 255, 255, 255))
        y_cursor += line_h + CAPTION_PADDING

    return np.array(img)


def _build_captions(script: str, total_duration: float) -> list[ImageClip]:
    """Split script into word-chunks and create timed caption ImageClips."""
    words = script.split()
    chunks = [
        " ".join(words[i: i + CAPTION_WORDS_PER_CHUNK])
        for i in range(0, len(words), CAPTION_WORDS_PER_CHUNK)
    ]
    if not chunks:
        return []

    chunk_dur = total_duration / len(chunks)
    font = _load_font(CAPTION_FONT_SIZE)
    y_pos = int(VIDEO_HEIGHT * CAPTION_Y_RATIO)
    caption_clips = []

    for idx, chunk in enumerate(chunks):
        frame = _make_caption_frame(chunk, VIDEO_WIDTH, font)
        clip = (
            ImageClip(frame, ismask=False)
            .set_start(idx * chunk_dur)
            .set_duration(chunk_dur)
            .set_position(("center", y_pos))
        )
        caption_clips.append(clip)

    return caption_clips


# ── Video clip processing ────────────────────────────────────────────────────

def _crop_to_portrait(clip: VideoFileClip) -> VideoFileClip:
    """Center-crop a video clip to 1080x1920 portrait format."""
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT  # ~0.5625
    clip_ratio = clip.w / clip.h

    if clip_ratio > target_ratio:
        # Wider than portrait — scale by height, crop sides
        scale = VIDEO_HEIGHT / clip.h
        new_w = int(clip.w * scale)
        clip = clip.resize((new_w, VIDEO_HEIGHT))
        x1 = (new_w - VIDEO_WIDTH) // 2
        clip = clip.crop(x1=x1, x2=x1 + VIDEO_WIDTH)
    else:
        # Taller than portrait — scale by width, crop top/bottom
        scale = VIDEO_WIDTH / clip.w
        new_h = int(clip.h * scale)
        clip = clip.resize((VIDEO_WIDTH, new_h))
        y1 = (new_h - VIDEO_HEIGHT) // 2
        clip = clip.crop(y1=y1, y2=y1 + VIDEO_HEIGHT)

    return clip.resize((VIDEO_WIDTH, VIDEO_HEIGHT))


def _build_clip_video(clip_paths: list[Path], target_duration: float):
    """Assemble stock video clips into a portrait video matching target_duration."""
    if not clip_paths:
        log.warning("No clips available — using black fallback")
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=target_duration)

    processed = []
    for path in clip_paths:
        try:
            raw = VideoFileClip(str(path), audio=False)
            portrait = _crop_to_portrait(raw)
            processed.append(portrait)
            log.info("Loaded clip %s (%.1fs)", path.name, raw.duration)
        except Exception as exc:
            log.warning("Skipping clip %s: %s", path.name, exc)

    if not processed:
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=target_duration)

    # Concatenate and loop until we cover target_duration
    base = concatenate_videoclips(processed, method="compose")
    while base.duration < target_duration:
        base = concatenate_videoclips(
            [base, concatenate_videoclips(processed, method="compose")],
            method="compose",
        )

    return base.subclip(0, target_duration)


# ── Main entry point ─────────────────────────────────────────────────────────

def create_video(
    script: str,
    audio_path: Path,
    keywords: list[str],
    output_path: Path,
    temp_dir: Path,
    topic: str = "",
    **_kwargs,
) -> Path:
    """
    Full pipeline: fetch stock clips -> portrait crop -> captions -> audio -> MP4.
    Returns *output_path*.
    """
    log.info("Starting video creation...")

    # 1. Get audio duration
    audio = AudioFileClip(str(audio_path))
    duration = audio.duration
    log.info("Audio duration: %.2fs", duration)

    # 2. Fetch stock video clips from Pexels
    clips_dir = temp_dir / "clips"
    search_terms = keywords if keywords else [topic or "cinematic"]
    clip_paths = fetch_clips(keywords=search_terms, output_dir=clips_dir, num_clips=5)

    # 3. Build portrait video from clips
    base = _build_clip_video(clip_paths, duration)

    # 4. Build caption overlays
    captions = _build_captions(script, duration)

    # 5. Composite captions onto base video
    layers = [base] + captions
    final = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))

    # 6. Attach voiceover
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
        logger=None,
        threads=4,
        preset="fast",
    )

    audio.close()
    base.close()
    final.close()

    log.info("Video ready: %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)
    return output_path
