"""
Generates short video clips using Google Veo 2 via the Google AI Studio API.

Each call generates one 8-second 16:9 video clip from a text prompt.
For a 2-minute video, 4 clips are generated then looped/tiled to fill duration.

Requires: GOOGLE_AI_STUDIO_API_KEY and google-genai>=1.0.0
"""
import time
from pathlib import Path

from google import genai
from google.genai import types

from config import GOOGLE_AI_STUDIO_API_KEY
from utils.logger import get_logger

log = get_logger(__name__)

VEO_MODEL = "veo-2.0-generate-001"
CLIP_DURATION = 8  # seconds per clip (Veo 2 max)
POLL_INTERVAL = 15  # seconds between status polls
MAX_POLL_WAIT  = 300  # 5 minutes max per clip


def _build_kid_prompts(topic: str, keywords: list[str]) -> list[str]:
    """
    Build 4 child-friendly scene prompts for Veo 2 from topic + keywords.
    Each prompt is cinematic, colourful, and safe for kids.
    """
    base = [k for k in (keywords or []) if k][:4] or [topic]
    moods = [
        "colourful playful introduction scene, bright cheerful lighting, cartoon style",
        "close-up cute detail, soft focus, warm colours, children's storybook feel",
        "exciting moment of discovery, vibrant colours, joyful expression, animated style",
        "happy resolution ending scene, sunshine, smiling characters, gentle motion",
    ]
    prompts = []
    for i in range(4):
        term = base[i % len(base)]
        prompts.append(
            f"{term}, {moods[i]}, 4K, safe for kids, no text, no humans, "
            f"smooth camera motion, professional children's educational video"
        )
    return prompts


def generate_veo_clips(
    topic: str,
    keywords: list[str],
    output_dir: Path,
    retries: int = 2,
) -> list[Path]:
    """
    Generate 4 Veo 2 video clips (8s each) and save as .mp4 files.
    Returns list of saved clip paths (may be fewer than 4 if some fail).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=GOOGLE_AI_STUDIO_API_KEY)
    prompts = _build_kid_prompts(topic, keywords)
    paths: list[Path] = []

    for i, prompt in enumerate(prompts):
        clip_path = output_dir / f"clip_{i:02d}.mp4"
        log.info("Generating Veo 2 clip %d/4: %s...", i + 1, prompt[:60])

        for attempt in range(1, retries + 1):
            try:
                operation = client.models.generate_videos(
                    model=VEO_MODEL,
                    prompt=prompt,
                    config=types.GenerateVideoConfig(
                        aspect_ratio="16:9",
                        duration_seconds=CLIP_DURATION,
                    ),
                )

                # Poll until done
                waited = 0
                while not operation.done:
                    time.sleep(POLL_INTERVAL)
                    waited += POLL_INTERVAL
                    operation = client.operations.get(operation)
                    log.info("  clip %d: waiting... (%ds)", i + 1, waited)
                    if waited >= MAX_POLL_WAIT:
                        raise TimeoutError(f"Veo 2 clip {i+1} timed out after {waited}s")

                generated = operation.result.generated_videos
                if not generated:
                    raise RuntimeError(f"Veo 2 returned no video for clip {i+1}")

                # Download the first generated video
                client.files.download(
                    file=generated[0].video,
                    download_to_file=str(clip_path),
                )
                log.info("Clip %d saved -> %s (%.1f MB)", i + 1, clip_path,
                         clip_path.stat().st_size / 1e6)
                paths.append(clip_path)
                break

            except Exception as exc:
                log.warning("Veo clip %d attempt %d failed: %s", i + 1, attempt, exc)
                if attempt < retries:
                    time.sleep(10)
        else:
            log.warning("Veo clip %d failed after all retries — skipping", i + 1)

    log.info("Generated %d/4 Veo clips", len(paths))
    return paths
