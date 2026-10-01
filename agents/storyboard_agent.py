"""
Generates a scene-by-scene storyboard for an animated kids story video.

Each storyboard has 6-8 scenes. Each scene includes:
  - narration text (what the voiceover says)
  - character description (who is in the scene)
  - action (what is happening)
  - background (the setting)
  - image_prompt (ready-to-use Pollinations prompt in cartoon style)

Output schema:
{
  "title": "...",
  "style": "...",        # e.g. "Pixar 3D", "watercolour children's book"
  "character": "...",    # the main character kept consistent across all scenes
  "scenes": [
    {
      "scene_number": 1,
      "narration": "...",
      "action": "...",
      "background": "...",
      "image_prompt": "..."
    }, ...
  ]
}
"""
import json
import time

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from utils.logger import get_logger

log = get_logger(__name__)

STORYBOARD_SYSTEM = """You are a children's animated video director. You create vivid, colourful,
scene-by-scene storyboards for 1-2 minute educational animated videos aimed at kids aged 3-8.
Your image prompts must be detailed enough for an AI image generator to produce consistent,
child-safe cartoon illustrations. Always respond with valid JSON only — no markdown fences."""

STORYBOARD_TEMPLATE = """Create a cinematic storyboard for a children's animated educational feature video in 16:9 widescreen.

Topic: {title}
Learning goal: {premise}
Category: {category}
Art style: {style}
Main character: {character}

Rules:
- 5 to 7 scenes structured as a complete, heartwarming mini-story
- Each scene must have a short punchy title (2-4 words) for the on-screen scene badge
- Each scene's narration: 1-2 friendly, engaging sentences
- Consistent character appearance across ALL scenes (same colours, same features)
- Camera motion per scene: pick from "dolly_in", "pan_right", "pan_left", "push_tilt", "slow_pullback", "slow_zoom"
- Each image_prompt must:
    • Start with: "Pixar 3D animation style, 16:9 widescreen cinematic shot, "
    • Describe the character and exact action clearly
    • Include lighting: "warm volumetric lighting, rich textures, vibrant colors, 4k render, cinematic 35mm lens"
    • End with: "safe for kids, no text, no captions, no watermarks"

Return ONLY this JSON:
{{
  "title": "{title}",
  "style": "{style}",
  "character": "{character}",
  "scenes": [
    {{
      "scene_number": 1,
      "title": "Scene Name",
      "narration": "short friendly sentence for voiceover",
      "action": "what the character is doing",
      "background": "the setting/environment",
      "camera_motion": "dolly_in",
      "image_prompt": "full detailed 16:9 prompt for AI image generation"
    }}
  ]
}}"""

ART_STYLES = [
    "Disney Pixar 3D Animated Feature style",
    "Pixar 3D animation style with warm volumetric lighting",
    "colourful 3D Disney animation style",
    "vibrant 3D cinematic CGI storybook style",
]

CHARACTERS = [
    "a small curious blue rabbit with big ears and a red scarf",
    "a cheerful yellow duckling with an orange beak and tiny wings",
    "a friendly round green frog with big sparkly eyes",
    "a tiny brave purple elephant with a flower on its head",
    "a jolly orange fox cub with a fluffy white-tipped tail",
]


def generate_storyboard(topic: dict, retries: int = 3) -> dict:
    """
    Generate a 7-scene storyboard for an animated kids educational video.
    `topic` is one entry from kids_topics.KIDS_TOPICS.
    Returns a storyboard dict with scenes list.
    """
    import random
    style = random.choice(ART_STYLES)
    character = random.choice(CHARACTERS)

    prompt = STORYBOARD_TEMPLATE.format(
        title=topic["title"],
        premise=topic["premise"],
        category=topic["category"],
        style=style,
        character=character,
    )
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating storyboard for '%s' (attempt %d)...", topic["title"], attempt)
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=4000,
                system=STORYBOARD_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            if not raw:
                raise ValueError("Empty response from Claude API")
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            result = json.loads(raw)

            if "scenes" not in result or len(result["scenes"]) < 4:
                raise ValueError(f"Storyboard has too few scenes: {len(result.get('scenes', []))}")

            log.info("Storyboard generated: %d scenes, style='%s'",
                     len(result["scenes"]), result.get("style", "?"))
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Storyboard error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Storyboard generation failed after {retries} attempts")
