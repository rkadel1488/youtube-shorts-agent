"""
Creates a 1080x1920 YouTube Short from:
  - Cricket stock footage from Pexels (portrait clips)
  - Copyright-free background music (no voiceover)
  - Match info title card + scrolling caption overlays (Pillow)

Pipeline:
  1. Fetch cricket video clips from Pexels
  2. Crop / resize each clip to 1080x1920 portrait
  3. Concatenate clips to fixed SHORT_DURATION seconds
  4. Download royalty-free background music
  5. Mix music at low volume into the video
  6. Render title card (match name) + caption overlays
  7. Composite all layers and export MP4
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

from agents.music_agent import download_music
from agents.video_clip_agent import fetch_clips
from config import VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
from utils.logger import get_logger

log = get_logger(__name__)

SHORT_DURATION   = 28      # seconds — ideal for Shorts completion rate
MUSIC_VOLUME     = 0.18    # background music volume (0.0–1.0)

# ── Caption / overlay styling ────────────────────────────────────────────────
CAPTION_FONT_SIZE  = 62
CAPTION_MAX_CHARS  = 26
CAPTION_Y_RATIO    = 0.76
CAPTION_PADDING    = 20
CAPTION_BG_ALPHA   = 190
CAPTION_WORDS_PER_CHUNK = 5

TITLE_FONT_SIZE    = 52
TITLE_Y_RATIO      = 0.06   # top of screen

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


# ── Text rendering helpers ────────────────────────────────────────────────────

def _render_text_box(
    text: str,
    width: int,
    font,
    max_chars: int,
    bg_color: tuple = (0, 0, 0),
    text_color: tuple = (255, 255, 255),
    bg_alpha: int = 190,
) -> np.ndarray:
    """Render text with rounded background box, return RGBA numpy array."""
    wrapped = textwrap.fill(text, width=max_chars)
    lines = wrapped.split("\n")

    dummy = Image.new("RGBA", (1, 1))
    draw  = ImageDraw.Draw(dummy)
    bboxes  = [draw.textbbox((0, 0), line, font=font) for line in lines]
    text_w  = max(bb[2] - bb[0] for bb in bboxes)
    line_h  = max(bb[3] - bb[1] for bb in bboxes)
    total_h = line_h * len(lines) + CAPTION_PADDING * (len(lines) - 1)

    box_w = text_w + CAPTION_PADDING * 4
    box_h = total_h + CAPTION_PADDING * 2
    img   = Image.new("RGBA", (width, box_h + CAPTION_PADDING * 2), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(img)

    x0, y0 = (width - box_w) // 2, CAPTION_PADDING
    draw.rounded_rectangle(
        [x0, y0, x0 + box_w, y0 + box_h],
        radius=16,
        fill=(*bg_color, bg_alpha),
    )

    y_cursor = y0 + CAPTION_PADDING
    for line, bbox in zip(lines, bboxes):
        lw = bbox[2] - bbox[0]
        lx = (width - lw) // 2
        draw.text((lx + 2, y_cursor + 2), line, font=font, fill=(0, 0, 0, 180))
        draw.text((lx, y_cursor), line, font=font, fill=(*text_color, 255))
        y_cursor += line_h + CAPTION_PADDING

    return np.array(img)


# ── Overlay builders ──────────────────────────────────────────────────────────

def _build_title_card(topic: str, duration: float) -> ImageClip:
    """Persistent title bar shown for the first 5 seconds at the top."""
    font  = _load_font(TITLE_FONT_SIZE)
    frame = _render_text_box(
        topic[:60], VIDEO_WIDTH, font, max_chars=30,
        bg_color=(180, 0, 0), text_color=(255, 255, 255), bg_alpha=220,
    )
    y_pos = int(VIDEO_HEIGHT * TITLE_Y_RATIO)
    return (
        ImageClip(frame, ismask=False)
        .set_start(0)
        .set_duration(min(5.0, duration))
        .set_position(("center", y_pos))
    )


def _build_captions(script: str, duration: float) -> list[ImageClip]:
    """Split script into word-chunks and create timed caption overlays."""
    words  = script.split()
    chunks = [
        " ".join(words[i: i + CAPTION_WORDS_PER_CHUNK])
        for i in range(0, len(words), CAPTION_WORDS_PER_CHUNK)
    ]
    if not chunks:
        return []

    chunk_dur = duration / len(chunks)
    font  = _load_font(CAPTION_FONT_SIZE)
    y_pos = int(VIDEO_HEIGHT * CAPTION_Y_RATIO)
    clips = []

    for idx, chunk in enumerate(chunks):
        frame = _render_text_box(chunk, VIDEO_WIDTH, font, max_chars=CAPTION_MAX_CHARS)
        clip  = (
            ImageClip(frame, ismask=False)
            .set_start(idx * chunk_dur)
            .set_duration(chunk_dur)
            .set_position(("center", y_pos))
        )
        clips.append(clip)

    return clips


# ── Video clip processing ────────────────────────────────────────────────────

def _crop_to_portrait(clip: VideoFileClip) -> VideoFileClip:
    """Center-crop a clip to 1080x1920 portrait."""
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
    clip_ratio   = clip.w / clip.h

    if clip_ratio > target_ratio:
        scale = VIDEO_HEIGHT / clip.h
        new_w = int(clip.w * scale)
        clip  = clip.resize((new_w, VIDEO_HEIGHT))
        x1    = (new_w - VIDEO_WIDTH) // 2
        clip  = clip.crop(x1=x1, x2=x1 + VIDEO_WIDTH)
    else:
        scale = VIDEO_WIDTH / clip.w
        new_h = int(clip.h * scale)
        clip  = clip.resize((VIDEO_WIDTH, new_h))
        y1    = (new_h - VIDEO_HEIGHT) // 2
        clip  = clip.crop(y1=y1, y2=y1 + VIDEO_HEIGHT)

    return clip.resize((VIDEO_WIDTH, VIDEO_HEIGHT))


def _build_clip_video(clip_paths: list[Path], target_duration: float):
    """Assemble portrait cricket clips to fill target_duration."""
    if not clip_paths:
        log.warning("No clips — using black fallback")
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=target_duration)

    processed = []
    for path in clip_paths:
        try:
            raw      = VideoFileClip(str(path), audio=False)
            portrait = _crop_to_portrait(raw)
            processed.append(portrait)
            log.info("Loaded clip %s (%.1fs)", path.name, raw.duration)
        except Exception as exc:
            log.warning("Skipping clip %s: %s", path.name, exc)

    if not processed:
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=target_duration)

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
    keywords: list[str],
    output_path: Path,
    temp_dir: Path,
    topic: str = "",
    **_kwargs,
) -> Path:
    """
    Full pipeline: cricket clips → portrait → music → captions → MP4.
    No voiceover — background music only.
    Returns *output_path*.
    """
    log.info("Starting cricket highlight video creation...")

    duration = SHORT_DURATION

    # 1. Fetch cricket stock clips from Pexels
    clips_dir    = temp_dir / "clips"
    search_terms = keywords if keywords else ["cricket match", "cricket stadium", "cricket batting"]
    clip_paths   = fetch_clips(keywords=search_terms, output_dir=clips_dir, num_clips=6)

    # 2. Build portrait video from clips
    base = _build_clip_video(clip_paths, duration)

    # 3. Download royalty-free background music
    music_path = download_music(temp_dir / "music.mp3")
    if music_path and music_path.exists():
        music_clip = AudioFileClip(str(music_path))
        # Loop music if shorter than video
        if music_clip.duration < duration:
            loops = int(duration / music_clip.duration) + 1
            from moviepy.editor import concatenate_audioclips
            music_clip = concatenate_audioclips([music_clip] * loops)
        music_clip = music_clip.subclip(0, duration).volumex(MUSIC_VOLUME)
        base = base.set_audio(music_clip)
        log.info("Background music added at %.0f%% volume", MUSIC_VOLUME * 100)
    else:
        log.info("No music — proceeding without audio")

    # 4. Build overlays: title card + caption chunks
    title_clip   = _build_title_card(topic or "Cricket Highlights", duration)
    caption_clips = _build_captions(script, duration)

    # 5. Composite all layers
    layers = [base, title_clip] + caption_clips
    final  = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))

    # 6. Export
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

    base.close()
    final.close()

    log.info("Video ready: %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)
    return output_path
