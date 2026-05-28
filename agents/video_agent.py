"""
Creates a 1080x1920 YouTube Short from:
  - A downloaded CC-licensed cricket Short (real match footage)
  - Copyright-free YouTube Audio Library background music
  - Match title card + caption text overlays (Pillow)

Pipeline:
  1. Download a CC-licensed cricket Short from YouTube
  2. Trim to SHORT_DURATION seconds and crop to portrait 9:16
  3. Download a YouTube Audio Library music track
  4. Mix music at low volume (original video audio stripped)
  5. Overlay: red title card (top) + caption chunks (bottom)
  6. Export final MP4
"""
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
    concatenate_videoclips,
)

from agents.music_agent import download_music
from agents.video_clip_agent import fetch_clips
from agents.yt_shorts_agent import get_cc_cricket_short
from config import VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
from utils.logger import get_logger

log = get_logger(__name__)

SHORT_DURATION       = 28     # seconds
MUSIC_VOLUME         = 0.20   # background music level

CAPTION_FONT_SIZE    = 62
CAPTION_MAX_CHARS    = 26
CAPTION_Y_RATIO      = 0.76
CAPTION_PADDING      = 20
CAPTION_BG_ALPHA     = 190
CAPTION_WORDS_PER_CHUNK = 5

TITLE_FONT_SIZE      = 50
TITLE_Y_RATIO        = 0.05

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


def _render_text_box(text, width, font, max_chars,
                     bg_color=(0, 0, 0), text_color=(255, 255, 255), bg_alpha=190):
    wrapped = textwrap.fill(text, width=max_chars)
    lines   = wrapped.split("\n")
    dummy   = Image.new("RGBA", (1, 1))
    draw    = ImageDraw.Draw(dummy)
    bboxes  = [draw.textbbox((0, 0), line, font=font) for line in lines]
    text_w  = max(bb[2] - bb[0] for bb in bboxes)
    line_h  = max(bb[3] - bb[1] for bb in bboxes)
    total_h = line_h * len(lines) + CAPTION_PADDING * (len(lines) - 1)
    box_w   = text_w + CAPTION_PADDING * 4
    box_h   = total_h + CAPTION_PADDING * 2
    img     = Image.new("RGBA", (width, box_h + CAPTION_PADDING * 2), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(img)
    x0, y0 = (width - box_w) // 2, CAPTION_PADDING
    draw.rounded_rectangle([x0, y0, x0 + box_w, y0 + box_h],
                           radius=16, fill=(*bg_color, bg_alpha))
    y_cursor = y0 + CAPTION_PADDING
    for line, bbox in zip(lines, bboxes):
        lw = bbox[2] - bbox[0]
        lx = (width - lw) // 2
        draw.text((lx + 2, y_cursor + 2), line, font=font, fill=(0, 0, 0, 180))
        draw.text((lx,     y_cursor),     line, font=font, fill=(*text_color, 255))
        y_cursor += line_h + CAPTION_PADDING
    return np.array(img)


def _build_title_card(topic: str, duration: float) -> ImageClip:
    font  = _load_font(TITLE_FONT_SIZE)
    frame = _render_text_box(topic[:55], VIDEO_WIDTH, font, max_chars=28,
                             bg_color=(180, 0, 0), text_color=(255, 255, 255), bg_alpha=225)
    return (ImageClip(frame, ismask=False)
            .set_start(0)
            .set_duration(min(6.0, duration))
            .set_position(("center", int(VIDEO_HEIGHT * TITLE_Y_RATIO))))


def _build_captions(script: str, duration: float) -> list[ImageClip]:
    words  = script.split()
    chunks = [" ".join(words[i: i + CAPTION_WORDS_PER_CHUNK])
              for i in range(0, len(words), CAPTION_WORDS_PER_CHUNK)]
    if not chunks:
        return []
    chunk_dur = duration / len(chunks)
    font      = _load_font(CAPTION_FONT_SIZE)
    y_pos     = int(VIDEO_HEIGHT * CAPTION_Y_RATIO)
    clips     = []
    for idx, chunk in enumerate(chunks):
        frame = _render_text_box(chunk, VIDEO_WIDTH, font, max_chars=CAPTION_MAX_CHARS)
        clips.append(
            ImageClip(frame, ismask=False)
            .set_start(idx * chunk_dur)
            .set_duration(chunk_dur)
            .set_position(("center", y_pos))
        )
    return clips


def _crop_to_portrait(clip: VideoFileClip) -> VideoFileClip:
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


def _build_base_video(cc_short_path: Path | None, keywords: list[str],
                      clips_dir: Path, duration: float):
    """
    Use the downloaded CC cricket Short as base.
    Falls back to Pexels stock clips if download failed.
    """
    if cc_short_path and cc_short_path.exists():
        try:
            raw = VideoFileClip(str(cc_short_path), audio=False)
            portrait = _crop_to_portrait(raw)
            # Trim to duration; if shorter, loop it
            if portrait.duration >= duration:
                return portrait.subclip(0, duration)
            loops = int(duration / portrait.duration) + 1
            looped = concatenate_videoclips([portrait] * loops, method="compose")
            return looped.subclip(0, duration)
        except Exception as exc:
            log.warning("Could not load CC Short, falling back to Pexels: %s", exc)

    # Fallback: Pexels cricket stock clips
    log.info("Using Pexels cricket stock clips as fallback...")
    clip_paths = fetch_clips(keywords=keywords or ["cricket match", "cricket stadium"],
                             output_dir=clips_dir, num_clips=6)
    if not clip_paths:
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=duration)

    processed = []
    for path in clip_paths:
        try:
            raw = VideoFileClip(str(path), audio=False)
            processed.append(_crop_to_portrait(raw))
        except Exception as exc:
            log.warning("Skipping Pexels clip %s: %s", path.name, exc)

    if not processed:
        return ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=duration)

    base = concatenate_videoclips(processed, method="compose")
    while base.duration < duration:
        base = concatenate_videoclips(
            [base, concatenate_videoclips(processed, method="compose")], method="compose")
    return base.subclip(0, duration)


def create_video(
    script: str,
    keywords: list[str],
    output_path: Path,
    temp_dir: Path,
    topic: str = "",
    **_kwargs,
) -> Path:
    """
    Full pipeline: CC cricket Short + YT Audio Library music + overlays → MP4.
    Returns *output_path*.
    """
    log.info("Starting cricket highlight video creation...")
    duration = SHORT_DURATION

    # 1. Download a CC-licensed cricket Short from YouTube
    log.info("Searching for CC-licensed cricket Short on YouTube...")
    cc_short = get_cc_cricket_short(temp_dir / "cc_short.mp4", topic=topic)

    # 2. Build portrait base video
    clips_dir = temp_dir / "clips"
    base = _build_base_video(cc_short, keywords, clips_dir, duration)

    # 3. Download YouTube Audio Library music
    log.info("Downloading YouTube Audio Library music track...")
    music_path = download_music(temp_dir / "music.mp3")
    if music_path and music_path.exists():
        try:
            music_clip = AudioFileClip(str(music_path))
            if music_clip.duration < duration:
                from moviepy.editor import concatenate_audioclips
                loops = int(duration / music_clip.duration) + 1
                music_clip = concatenate_audioclips([music_clip] * loops)
            music_clip = music_clip.subclip(0, duration).volumex(MUSIC_VOLUME)
            base = base.set_audio(music_clip)
            log.info("Music added at %.0f%% volume", MUSIC_VOLUME * 100)
        except Exception as exc:
            log.warning("Could not add music: %s", exc)

    # 4. Build overlays
    title_clip    = _build_title_card(topic or "Cricket Highlights", duration)
    caption_clips = _build_captions(script, duration)

    # 5. Composite
    layers = [base, title_clip] + caption_clips
    final  = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))

    # 6. Export
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log.info("Rendering -> %s", output_path)
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
