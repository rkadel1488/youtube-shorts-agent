"""
Generates a YouTube Shorts script + supporting metadata using Claude.

Output schema (JSON):
{
  "topic": "...",
  "hook": "...",
  "script": "...",
  "keywords": ["word1", "word2", ...]   # for Pexels search
}
"""
import json
import time

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, NICHES
from utils.logger import get_logger

log = get_logger(__name__)
_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an expert YouTube Shorts scriptwriter.
Your scripts go viral because they open with an irresistible hook, use short punchy sentences,
build curiosity, reveal something surprising, and end with a clear call-to-action.
Always respond with valid JSON only — no markdown fences, no extra commentary."""

SCRIPT_TEMPLATE = """Write a NEW, unique YouTube Shorts script for the niche: {niche_label}.

Rules:
- Total spoken length: 20–27 seconds (~60-75 words)
- Hook (first sentence): shock/curiosity-gap, under 12 words
- Body: short sentences (max 10 words each), build tension, deliver a surprising fact or reveal
- CTA (last sentence): "Follow for [specific benefit]."
- NEVER use a topic already covered. Be creative.

Return ONLY this JSON (no markdown):
{{
  "topic": "one-line topic description",
  "hook": "the opening hook line only",
  "script": "full script including hook, body, and CTA",
  "keywords": ["3-5 single English words useful for finding relevant stock video on Pexels"]
}}"""


def generate_script(niche: dict, retries: int = 3) -> dict:
    """
    Call Claude to generate a script for *niche*.
    Returns a dict with keys: topic, hook, script, keywords.
    """
    prompt = SCRIPT_TEMPLATE.format(niche_label=niche["label"])

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating script for niche '%s' (attempt %d)…", niche["label"], attempt)
            message = _client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            result = json.loads(raw)

            # Validate required keys
            for key in ("topic", "hook", "script", "keywords"):
                if key not in result:
                    raise ValueError(f"Missing key '{key}' in Claude response")

            log.info("Script generated: '%s'", result["topic"])
            return result

        except json.JSONDecodeError as exc:
            log.warning("JSON parse error on attempt %d: %s", attempt, exc)
        except Exception as exc:
            log.warning("Script generation error on attempt %d: %s", attempt, exc)

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Script generation failed after {retries} attempts")
