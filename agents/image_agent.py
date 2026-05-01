"""
Generates 4 cinematic AI images per Short using Pollinations.ai (100% free, no API key).
Uses the FLUX model with exact 1080x1920 (9:16) resolution for YouTube Shorts.

Each image matches a scene in the script: opening, build, reveal, close.
Visual style is automatically tailored per niche.
"""
import random
import time
import urllib.parse
from pathlib import Path

import requests

from config import VIDEO_HEIGHT, VIDEO_WIDTH
from utils.logger import get_logger

log = get_logger(__name__)

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"

# Cinematic style per niche
NICHE_STYLES = {
    "dark_psychology": (
        "dark moody atmosphere, psychological thriller, "
        "dramatic chiaroscuro lighting, deep shadows, mysterious, cinematic 8K"
    ),
    "ai_tools": (
        "futuristic digital world, glowing holographic interface, "
        "cyberpunk neon blue and purple, cinematic 8K"
    ),
    "history_facts": (
        "epic historical cinematic scene, dramatic golden hour lighting, "
        "ancient civilization, photorealistic documentary 8K"
    ),
    "money_secrets": (
        "luxury wealth lifestyle, sleek modern architecture, "
        "gold and black palette, editorial cinematic 8K"
    ),
    "space_universe": (
        "breathtaking cosmic vista, deep space nebula, "
        "stars and galaxies, epic galactic scale, NASA quality 8K"
    ),
}

DEFAULT_STYLE = "cinematic, dramatic lighting, photorealistic, 8K, highly detailed"

SCENE_TEMPLATES = [
    "Wide establishing shot: {topic}, dramatic opening",
    "Close-up: {topic}, intense focus, emotional depth",
    "Reveal moment: {topic}, tension and discovery",
    "Powerful closing image: {topic}, impactful final frame",
]


def _build_prompts(topic: str, niche_name: str, keywords: list[str]) -> list[str]:
    """Build 4 FLUX prompts tailored to the topic and niche."""
    style = NICHE_STYLES.get(niche_name, DEFAULT_STYLE)
    kw_str = ", ".join(k for k in keywords[:3] if k) if keywords else topic
    prompts = []
    for template in SCENE_TEMPLATES:
        scene = template.format(topic=topic)
        prompt = (
            f"{scene}, {kw_str}, {style}, "
            f"vertical portrait format, no text, no watermarks, no logos"
        )
        prompts.append(prompt)
    return prompts


def generate_images(
    topic: str,
    niche: dict,
    keywords: list[str],
    output_dir: Path,
    retries: int = 3,
) -> list[Path]:
    """
    Generate 4 AI images using Pollinations.ai FLUX model (free, no API key).
    Returns a list of saved JPEG image paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    prompts = _build_prompts(topic, niche.get("name", ""), keywords)
    paths: list[Path] = []

    for i, prompt in enumerate(prompts):
        img_path = output_dir / f"scene_{i:02d}.jpg"
        seed = random.randint(1, 999999)

        url = POLLINATIONS_URL.format(prompt=urllib.parse.quote(prompt))
        params = {
            "width": VIDEO_WIDTH,
            "height": VIDEO_HEIGHT,
            "seed": seed,
            "model": "flux",
            "nologo": "true",
            "enhance": "true",
        }

        for attempt in range(1, retries + 1):
            try:
                log.info("Generating image %d/%d via Pollinations (attempt %d)...", i + 1, len(prompts), attempt)
                resp = requests.get(url, params=params, timeout=90)
                resp.raise_for_status()

                # Validate it's actually an image
                content_type = resp.headers.get("content-type", "")
                if "image" not in content_type and len(resp.content) < 10_000:
                    raise ValueError(f"Response doesn't look like an image: {content_type}")

                with open(img_path, "wb") as f:
                    f.write(resp.content)

                log.info("Image %d saved -> %s (%d KB)", i + 1, img_path, len(resp.content) // 1024)
                paths.append(img_path)
                break

            except Exception as exc:
                log.warning("Image %d attempt %d failed: %s", i + 1, attempt, exc)
                if attempt < retries:
                    time.sleep(2 ** attempt)
        else:
            log.warning("Image %d failed after all retries — skipping", i + 1)

        # Small delay between images to be polite to the free API
        time.sleep(1)

    log.info("Generated %d/%d images successfully", len(paths), len(prompts))
    return paths
