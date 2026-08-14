"""
Generates a YouTube thumbnail (1280x720) for each video.

Design:
  - Best available stock image as full-bleed background
  - Dark gradient overlay (bottom-up) for text legibility
  - Bold white title text with drop-shadow
  - Contrasting accent bar (red) with hook text
  - Subtle vignette for cinematic feel
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from utils.logger import get_logger

log = get_logger(__name__)

THUMB_WIDTH  = 1280
THUMB_HEIGHT = 720

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines, current = [], ""
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    for word in words:
        test = f"{current} {word}".strip()
        w = draw.textbbox((0, 0), test, font=font)[2]
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def create_thumbnail(
    title: str,
    hook: str,
    image_paths: list[Path],
    output_path: Path,
) -> Path:
    """
    Build a 1280x720 YouTube thumbnail and save to output_path.
    Uses the first available image_path as the background.
    Returns output_path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── background ──────────────────────────────────────────────────────────
    if image_paths:
        bg = Image.open(image_paths[0]).convert("RGB")
    else:
        bg = Image.new("RGB", (THUMB_WIDTH, THUMB_HEIGHT), (20, 20, 30))

    # Center-crop to 1280x720
    bg_w, bg_h = bg.size
    target_ratio = THUMB_WIDTH / THUMB_HEIGHT
    if bg_w / bg_h > target_ratio:
        new_w = int(bg_h * target_ratio)
        x0 = (bg_w - new_w) // 2
        bg = bg.crop((x0, 0, x0 + new_w, bg_h))
    else:
        new_h = int(bg_w / target_ratio)
        y0 = (bg_h - new_h) // 2
        bg = bg.crop((0, y0, bg_w, y0 + new_h))
    bg = bg.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)

    # Slight blur so text pops
    bg = bg.filter(ImageFilter.GaussianBlur(radius=1.5))

    canvas = bg.convert("RGBA")

    # ── dark gradient overlay (bottom 55%) ───────────────────────────────────
    gradient = Image.new("RGBA", (THUMB_WIDTH, THUMB_HEIGHT), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(gradient)
    grad_start = int(THUMB_HEIGHT * 0.35)
    for y in range(grad_start, THUMB_HEIGHT):
        alpha = int(220 * ((y - grad_start) / (THUMB_HEIGHT - grad_start)) ** 0.7)
        grad_draw.line([(0, y), (THUMB_WIDTH, y)], fill=(0, 0, 0, alpha))
    canvas = Image.alpha_composite(canvas, gradient)

    # ── vignette ────────────────────────────────────────────────────────────
    vignette = Image.new("RGBA", (THUMB_WIDTH, THUMB_HEIGHT), (0, 0, 0, 0))
    vig_draw = ImageDraw.Draw(vignette)
    for i in range(60):
        alpha = int(100 * (i / 60) ** 2)
        pad = i * 6
        vig_draw.rectangle(
            [pad, pad, THUMB_WIDTH - pad, THUMB_HEIGHT - pad],
            outline=(0, 0, 0, alpha),
            width=6,
        )
    canvas = Image.alpha_composite(canvas, vignette)

    draw = ImageDraw.Draw(canvas)

    # ── accent bar (hook text) ────────────────────────────────────────────────
    hook_text = hook.upper()[:55]
    hook_font = _load_font(38)
    bar_h = 58
    bar_y = THUMB_HEIGHT - 68
    draw.rectangle([0, bar_y, THUMB_WIDTH, bar_y + bar_h], fill=(210, 30, 30, 230))

    dummy = Image.new("RGBA", (1, 1))
    ddraw = ImageDraw.Draw(dummy)
    hbbox = ddraw.textbbox((0, 0), hook_text, font=hook_font)
    hx = (THUMB_WIDTH - (hbbox[2] - hbbox[0])) // 2
    hy = bar_y + (bar_h - (hbbox[3] - hbbox[1])) // 2
    draw.text((hx + 2, hy + 2), hook_text, font=hook_font, fill=(0, 0, 0, 180))
    draw.text((hx, hy), hook_text, font=hook_font, fill=(255, 255, 255, 255))

    # ── main title text ───────────────────────────────────────────────────────
    title_font = _load_font(82)
    title_lines = _wrap_text(title, title_font, THUMB_WIDTH - 80)
    if len(title_lines) > 2:
        title_font = _load_font(62)
        title_lines = _wrap_text(title, title_font, THUMB_WIDTH - 80)

    dummy2 = Image.new("RGBA", (1, 1))
    d2 = ImageDraw.Draw(dummy2)
    line_bboxes = [d2.textbbox((0, 0), l, font=title_font) for l in title_lines]
    line_h = max(b[3] - b[1] for b in line_bboxes)
    total_text_h = line_h * len(title_lines) + 12 * (len(title_lines) - 1)
    zone_top = int(THUMB_HEIGHT * 0.35)
    zone_bot = bar_y - 12
    ty = zone_top + (zone_bot - zone_top - total_text_h) // 2

    for line, bbox in zip(title_lines, line_bboxes):
        lw = bbox[2] - bbox[0]
        tx = (THUMB_WIDTH - lw) // 2
        for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4), (4, 0), (-4, 0), (0, -4)]:
            draw.text((tx + dx, ty + dy), line, font=title_font, fill=(0, 0, 0, 200))
        draw.text((tx, ty), line, font=title_font, fill=(255, 255, 255, 255))
        ty += line_h + 12

    final = canvas.convert("RGB")
    final.save(str(output_path), "JPEG", quality=95)
    log.info("Thumbnail saved -> %s (%.1f KB)", output_path, output_path.stat().st_size / 1024)
    return output_path
