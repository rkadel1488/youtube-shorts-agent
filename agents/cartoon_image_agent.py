"""
Generates cartoon-style images for each storyboard scene using Pollinations.ai
(free, no API key required).

Each image uses the exact image_prompt from the storyboard, ensuring visual
consistency with the character and art style across all scenes.
"""
import time
import urllib.parse
from pathlib import Path

import requests
from PIL import Image

from config import VIDEO_HEIGHT, VIDEO_WIDTH
from utils.logger import get_logger

log = get_logger(__name__)

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
IMG_W = 1080
IMG_H = 1920


def _fetch_cartoon_image(prompt: str, output_path: Path, retries: int = 3) -> bool:
    """Fetch one cartoon image from Pollinations.ai. Returns True on success."""
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={IMG_W}&height={IMG_H}&nologo=true&enhance=true"

    for attempt in range(1, retries + 1):
        try:
            log.info("  Fetching cartoon image (attempt %d): %s...", attempt, prompt[:60])
            resp = requests.get(url, timeout=90, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(resp.content)

            # Verify it's a valid image and resize to target dimensions
            img = Image.open(output_path).convert("RGB")
            img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
            img.save(output_path, "JPEG", quality=92)

            log.info("  Cartoon image saved -> %s (%.0f KB)",
                     output_path.name, output_path.stat().st_size / 1024)
            return True

        except Exception as exc:
            log.warning("  Image attempt %d failed: %s", attempt, exc)
            if attempt < retries:
                time.sleep(3 * attempt)

    return False


def generate_cartoon_images(scenes: list[dict], output_dir: Path) -> list[Path]:
    """
    Generate one cartoon image per storyboard scene.
    `scenes` is the list from storyboard_agent output.
    Returns list of saved image paths (in scene order, skipping failures).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for scene in scenes:
        i = scene["scene_number"]
        prompt = scene.get("image_prompt", "")
        if not prompt:
            log.warning("Scene %d has no image_prompt — skipping", i)
            continue

        img_path = output_dir / f"scene_{i:02d}.jpg"
        success = _fetch_cartoon_image(prompt, img_path)
        if success:
            paths.append(img_path)
        else:
            log.warning("Scene %d image failed after all retries — skipping", i)

        time.sleep(2)  # be gentle with the free API

    log.info("Generated %d/%d cartoon scene images", len(paths), len(scenes))
    return paths
