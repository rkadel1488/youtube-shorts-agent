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
    CompositeAudioClip,
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


def _moment_label(text: str, duration: float) -> ImageClip:
    """Yellow pill label at the bottom-left showing 'MOMENT N' for the first 2 seconds."""
    font    = _load_font(42)
    dummy   = Image.new("RGBA", (1, 1))
    draw    = ImageDraw.Draw(dummy)
    bbox    = draw.textbbox((0, 0), text, font=font)
    text_w  = bbox[2] - bbox[0]
    text_h  = bbox[3] - bbox[1]
    pad     = 14
    box_w   = text_w + pad * 4
    box_h   = text_h + pad * 2
    margin  = 40

    img  = Image.new("RGBA", (box_w + margin, box_h + margin), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [margin // 2, margin // 2, margin // 2 + box_w, margin // 2 + box_h],
        radius=box_h // 2,
        fill=(255, 210, 0, 230),
    )
    draw.text(
        (margin // 2 + pad * 2, margin // 2 + pad),
        text, font=font, fill=(0, 0, 0, 255),
    )
    y_pos = VIDEO_HEIGHT - box_h - margin * 2
    return (
        ImageClip(np.array(img), ismask=False)
        .set_start(0)
        .set_duration(duration)
        .set_position((margin, y_pos))
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


# ── compilation entry ────────────────────────────────────────────────────────

def create_cricket_compilation(
    clips: list,
    clip_infos: list,
    output_path: Path,
    temp_dir: Path,
    voiceover_path: Path | None = None,
    on_screen_hook: str | None = None,
) -> Path:
    """
    Build a 'N Moments' compilation Short from multiple CC cricket clips.
    Each segment gets a 'MOMENT N' counter overlay for its first 2 seconds.
    Clips are separated by a brief black flash. Voiceover + music mixed in.
    on_screen_hook: large centred hook text shown for first 3.5s (for silent viewers).
    """
    from moviepy.editor import concatenate_videoclips, ColorClip as _CC

    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n = len(clips)
    seg_duration = max(6.0, SHORT_DURATION / n)   # distribute time evenly
    flash_duration = 0.3                           # black flash between moments

    segments = []
    for i, (clip_path, info) in enumerate(zip(clips, clip_infos)):
        raw = VideoFileClip(str(clip_path), audio=False)
        seg = _crop_portrait(raw)
        # Trim to segment duration
        if seg.duration > seg_duration:
            seg = seg.subclip(0, seg_duration)
        elif seg.duration < 3:
            raw.close()
            continue  # skip clips that are too short after crop

        # "MOMENT N" label overlay for first 2 seconds
        label_text = f"MOMENT {i + 1}"
        label = _moment_label(label_text, min(2.0, seg.duration))
        seg = CompositeVideoClip([seg, label], size=(VIDEO_WIDTH, VIDEO_HEIGHT))
        segments.append(seg)
        raw.close()

    if not segments:
        raise RuntimeError("No valid segments for cricket compilation")

    # Black flash between segments
    flash = _CC(color=(0, 0, 0), size=(VIDEO_WIDTH, VIDEO_HEIGHT), duration=flash_duration)
    parts = []
    for i, seg in enumerate(segments):
        parts.append(seg)
        if i < len(segments) - 1:
            parts.append(flash)

    video = concatenate_videoclips(parts, method="compose")
    duration = video.duration

    # Background music
    log.info("Downloading background music for compilation...")
    music_path = download_music(temp_dir / "music.mp3")

    if voiceover_path and voiceover_path.exists():
        try:
            vo = AudioFileClip(str(voiceover_path)).volumex(0.9)
            if music_path and music_path.exists():
                try:
                    music = AudioFileClip(str(music_path))
                    if music.duration < duration:
                        loops = int(duration / music.duration) + 1
                        music = concatenate_audioclips([music] * loops)
                    music = music.subclip(0, duration).volumex(0.15)
                    video = video.set_audio(CompositeAudioClip([music, vo]))
                    log.info("Voiceover + background music mixed")
                except Exception as exc:
                    log.warning("Music mix failed, using voiceover only: %s", exc)
                    video = video.set_audio(vo)
            else:
                video = video.set_audio(vo)
                log.info("Voiceover added as primary audio")
        except Exception as exc:
            log.warning("Voiceover mixing failed: %s", exc)
    elif music_path and music_path.exists():
        try:
            music = AudioFileClip(str(music_path))
            if music.duration < duration:
                loops = int(duration / music.duration) + 1
                music = concatenate_audioclips([music] * loops)
            music = music.subclip(0, duration).volumex(MUSIC_VOLUME)
            video = video.set_audio(music)
        except Exception as exc:
            log.warning("Could not add music: %s", exc)

    # Title overlay at the very top
    count_title = f"{len(segments)} Cricket Moments \U0001f92f"
    title = _title_overlay(count_title, min(4.0, duration))
    layers = [video, title]
    if on_screen_hook:
        layers.append(_hook_overlay(on_screen_hook, duration))
    final = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))

    log.info("Rendering compilation -> %s", output_path)
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

    log.info("Compilation done: %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)
    return output_path


# ── main entry ───────────────────────────────────────────────────────────────

def create_video(
    topic: str,
    output_path: Path,
    temp_dir: Path,
    cc_path: Path | None = None,
    voiceover_path: Path | None = None,
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

    # Mix audio: voiceover (primary) + background music (ambient)
    if voiceover_path and voiceover_path.exists():
        try:
            vo = AudioFileClip(str(voiceover_path))
            vo = vo.volumex(0.9)
            if music_path and music_path.exists():
                try:
                    music = AudioFileClip(str(music_path))
                    if music.duration < duration:
                        loops = int(duration / music.duration) + 1
                        music = concatenate_audioclips([music] * loops)
                    music = music.subclip(0, duration).volumex(0.15)
                    combined = CompositeAudioClip([music, vo])
                    base = base.set_audio(combined)
                    log.info("Voiceover + background music mixed")
                except Exception as exc:
                    log.warning("Music mix failed, using voiceover only: %s", exc)
                    base = base.set_audio(vo)
            else:
                base = base.set_audio(vo)
                log.info("Voiceover added as primary audio")
        except Exception as exc:
            log.warning("Voiceover mixing failed: %s", exc)
    elif music_path and music_path.exists():
        # Music-only path (existing code)
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
        log.info("Music unavailable — trying AI voiceover as fallback...")
        try:
            from agents.audio_agent import generate_voiceover
            vo_path = temp_dir / "voiceover_fallback.mp3"
            generate_voiceover(topic, vo_path)
            music = AudioFileClip(str(vo_path))
            base = base.set_audio(music)
            log.info("AI voiceover added as audio fallback")
        except Exception as exc:
            log.warning("AI voiceover fallback also failed: %s — video will be silent", exc)

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

    final.close()
    base.close()
    raw.close()

    log.info("Done: %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)
    return output_path


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
