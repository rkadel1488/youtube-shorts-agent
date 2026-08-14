"""
Generates 8 cinematic images per video by fetching keyword-matched stock photos
from the Pexels Photo API (free, requires PEXELS_API_KEY).

Each image matches a scene/mood derived from the script topic and keywords.
8 images cover a ~2-minute video with ~15s per scene.
"""
import random
import time
from pathlib import Path

import requests
from PIL import Image

from config import PEXELS_API_KEY, VIDEO_HEIGHT, VIDEO_WIDTH
from utils.logger import get_logger

log = get_logger(__name__)

PEXELS_PHOTO_URL = "https://api.pexels.com/v1/search"

SCENE_MOODS = [
    "wide establishing shot",
    "close-up dramatic detail",
    "tense atmospheric scene",
    "mysterious dark moment",
    "action intense",
    "cinematic silhouette",
    "emotional powerful moment",
    "dramatic finale reveal",
]


def _build_queries(topic: str, keywords: list[str]) -> list[str]:
    """Build 8 search queries tailored to the topic/keywords for visual variety."""
    base_terms = [k for k in (keywords or []) if k][:8] or [topic]
    queries = []
    for i in range(8):
        term = base_terms[i % len(base_terms)]
        queries.append(f"{term} {SCENE_MOODS[i]}")
    return queries


def _crop_landscape(img: Image.Image) -> Image.Image:
    """Center-crop a PIL image to the 1920x1080 landscape aspect ratio."""
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
    w, h = img.size
    if w / h > target_ratio:
        new_w = int(h * target_ratio)
        x0 = (w - new_w) // 2
        img = img.crop((x0, 0, x0 + new_w, h))
    else:
        new_h = int(w / target_ratio)
        y0 = (h - new_h) // 2
        img = img.crop((0, y0, w, y0 + new_h))
    return img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)


def generate_images(
    topic: str,
    keywords: list[str],
    output_dir: Path,
    retries: int = 3,
    **_kwargs,
) -> list[Path]:
    """
    Fetch 8 keyword-matched stock photos from Pexels, cropped to 1920x1080 landscape.
    Returns a list of saved JPEG image paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if not PEXELS_API_KEY:
        log.warning("PEXELS_API_KEY not set — cannot fetch stock images")
        return []

    queries = _build_queries(topic, keywords)
    paths: list[Path] = []

    for i, query in enumerate(queries):
        img_path = output_dir / f"scene_{i:02d}.jpg"

        for attempt in range(1, retries + 1):
            try:
                log.info("Fetching image %d/%d for '%s' (attempt %d)...", i + 1, len(queries), query, attempt)
                resp = requests.get(
                    PEXELS_PHOTO_URL,
                    headers={"Authorization": PEXELS_API_KEY},
                    params={"query": query, "per_page": 15, "orientation": "landscape"},
                    timeout=30,
                )
                resp.raise_for_status()
                photos = resp.json().get("photos", [])
                if not photos:
                    raise ValueError(f"No Pexels photos found for '{query}'")

                random.shuffle(photos)
                photo = photos[0]
                src = photo.get("src", {})
                url = src.get("large2x") or src.get("large") or src.get("original")
                if not url:
                    raise ValueError("Pexels photo has no usable source URL")

                img_resp = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
                img_resp.raise_for_status()

                tmp_path = output_dir / f"_raw_{i:02d}.jpg"
                with open(tmp_path, "wb") as f:
                    f.write(img_resp.content)

                img = Image.open(tmp_path).convert("RGB")
                img = _crop_landscape(img)
                img.save(img_path, "JPEG", quality=90)
                tmp_path.unlink(missing_ok=True)

                log.info("Image %d saved -> %s", i + 1, img_path)
                paths.append(img_path)
                break

            except Exception as exc:
                log.warning("Image %d attempt %d failed: %s", i + 1, attempt, exc)
                if attempt < retries:
                    time.sleep(2 ** attempt)
        else:
            log.warning("Image %d failed after all retries — skipping", i + 1)

        time.sleep(1)

    log.info("Generated %d/%d images successfully", len(paths), len(queries))
    return paths
