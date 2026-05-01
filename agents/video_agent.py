"""
Creates a 1080x1920 YouTube Short from:
  - AI-generated images (Google Imagen 3) with Ken Burns zoom/pan effect
  - An MP3 voiceover
  - Auto-generated caption overlays (Pillow — no ImageMagick needed)

Pipeline:
  1. Generate 4 AI images via Imagen 3
  2. Apply Ken Burns effect to each image (alternating zoom-in / zoom-out)
  3. Concatenate image clips to match audio length
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
    VideoClip,
    concatenate_videoclips,
)

from agents.image_agent import generate_images
from config import VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
from utils.logger import get_logger

log = get_logger(__name__)

# ── Caption styling ─────────────────────────────────────────────────────────
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


# ── Ken Burns effect ─────────────────────────────────────────────────────────

def _fit_image(img: Image.Image) -> Image.Image:
    """Resize and center-crop image to exactly 1080x1920 with a 10% padding border
    so there is room to zoom/pan without black edges."""
    pad_w = int(VIDEO_WIDTH * 1.12)
    pad_h = int(VIDEO_HEIGHT * 1.12)

    img_ratio = img.width / img.height
    target_ratio = pad_w / pad_h

    if img_ratio > target_ratio:
        new_h = pad_h
        new_w = int(img.width * pad_h / img.height)
    else:
        new_w = pad_w
        new_h = int(img.height * pad_w / img.width)

    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - pad_w) // 2
    top = (new_h - pad_h) // 2
    return img.crop((left, top, left + pad_w, top + pad_h))


def _ken_burns_clip(img_path: Path, duration: float, reverse: bool = False) -> VideoClip:
    """
    Wrap an image in a Ken Burns effect clip.
    Even-indexed images zoom in; odd-indexed images zoom out.
    """
    img = Image.open(img_path).convert("RGB")
    img_padded = _fit_image(img)
    pad_w, pad_h = img_padded.size
    img_array = np.array(img_padded)

    zoom_start = 1.0
    zoom_end = 0.90  # zoom in by ~10% over the clip duration

    def make_frame(t: float) -> np.ndarray:
        progress = (t / duration) if duration > 0 else 0
        if reverse:
            progress = 1.0 - progress

        scale = zoom_start - (zoom_start - zoom_end) * progress
        crop_w = int(pad_w * scale)
        crop_h = int(pad_h * scale)

        # Subtle horizontal drift
        drift_x = int((pad_w - crop_w) * 0.15 * progress)
        cx = pad_w // 2 + (drift_x if not reverse else -drift_x)
        cy = pad_h // 2

        left = max(0, cx - crop_w // 2)
        top = max(0, cy - crop_h // 2)
        right = min(pad_w, left + crop_w)
        bottom = min(pad_h, top + crop_h)

        cropped = img_array[top:bottom, left:right]
        resized = Image.fromarray(cropped).resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
        return np.array(resized)

    return VideoClip(make_frame, duration=duration).set_fps(VIDEO_FPS)


# ── Slideshow builder ────────────────────────────────────────────────────────

def _build_image_slideshow(img_paths: list[Path], target_duration: float):
    """Build base video from AI images with alternating Ken Burns effects."""
    if not img_paths:
        log.warning("No images available — using black fallback")
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=target_duration)

    per_img = target_duration / len(img_paths)
    clips = []

    for i, img_path in enumerate(img_paths):
        try:
            clip = _ken_burns_clip(img_path, per_img, reverse=(i % 2 == 1))
            clips.append(clip)
            log.info("Ken Burns clip %d created (%.1fs)", i + 1, per_img)
        except Exception as exc:
            log.warning("Skipping image %s: %s", img_path.name, exc)

    if not clips:
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=target_duration)

    # Loop if fewer images than needed (shouldn't happen with 4 images)
    while sum(c.duration for c in clips) < target_duration:
        clips.extend(clips[:])

    base = concatenate_videoclips(clips, method="compose")
    if base.duration > target_duration:
        base = base.subclip(0, target_duration)

    return base


# ── Main entry point ─────────────────────────────────────────────────────────

def create_video(
    script: str,
    audio_path: Path,
    keywords: list[str],
    output_path: Path,
    temp_dir: Path,
    topic: str = "",
    niche: dict | None = None,
) -> Path:
    """
    Full pipeline: generate AI images -> Ken Burns slideshow -> captions -> audio -> MP4.
    Returns *output_path*.
    """
    log.info("Starting video creation...")
    niche = niche or {"name": "dark_psychology", "label": "Dark Psychology"}

    # 1. Get audio duration
    audio = AudioFileClip(str(audio_path))
    duration = audio.duration
    log.info("Audio duration: %.2fs", duration)

    # 2. Generate AI images
    images_dir = temp_dir / "images"
    img_paths = generate_images(
        topic=topic or script[:60],
        niche=niche,
        keywords=keywords,
        output_dir=images_dir,
    )

    # 3. Build Ken Burns slideshow
    base = _build_image_slideshow(img_paths, duration)

    # 4. Build caption overlays
    captions = _build_captions(script, duration)

    # 5. Composite captions onto base
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
