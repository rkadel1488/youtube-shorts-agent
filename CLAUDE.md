# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# One-time YouTube OAuth setup (opens browser, saves youtube_token.json)
python setup_youtube_auth.py

# Run a single Short immediately (for testing)
python main.py --run-now
python main.py --run-now --slot 2   # slot 0=night, 1=morning, 2=afternoon, 3=evening

# Start the scheduler (runs indefinitely, fires at POSTING_TIMES)
python main.py
```

No test suite or linter is configured.

## Environment / Secrets

Copy `.env` (local) or set GitHub Actions secrets:

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude (script + SEO generation) |
| `GOOGLE_AI_STUDIO_API_KEY` | Gemini TTS voiceover |
| `PEXELS_API_KEY` | Present in config but unused — image generation now uses Pollinations.ai (free, no key) |
| `YOUTUBE_CLIENT_SECRETS` | JSON contents of `client_secrets.json` (GitHub secret) |
| `YOUTUBE_TOKEN` | JSON contents of `youtube_token.json` (GitHub secret) |
| `GEMINI_TTS_VOICE` | Default `Charon`; options: Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede |
| `POSTING_TIMES` | Comma-separated HH:MM times, default `02:00,08:00,14:00,20:00` |
| `MADE_FOR_KIDS` | `true`/`false`, default `false` |

## Architecture

The system is a linear 5-step pipeline orchestrated by `main.py::run_pipeline()`. Each step is an independent agent module:

```
main.py::run_pipeline()
  ├─ agents/script_agent.py  → Claude API → {topic, hook, script, keywords}
  ├─ agents/seo_agent.py     → Claude API → {title, description, tags, hashtags}
  ├─ agents/audio_agent.py   → Gemini TTS → voiceover.mp3
  ├─ agents/video_agent.py   → Pollinations FLUX (via image_agent) + MoviePy → final.mp4
  │    └─ agents/image_agent.py  → Pollinations.ai free API → 4 × scene_XX.jpg
  └─ agents/upload_agent.py  → YouTube Data API v3 → video ID
```

Each agent function signature is simple and self-contained — they receive plain Python types and return a path or dict. All agents implement a `retries` loop with exponential backoff.

**Niche rotation**: `config.py::NICHES` defines 4 niches. The active niche is selected by `_pick_niche(slot)` using `(day_of_year + slot) % len(NICHES)`, so the starting niche rotates every day.

**Output layout**: Each job writes to `output/<timestamp>_<niche>/` containing `script.json`, `seo.json`, `voiceover.mp3`, `final.mp4`, and `result.json`. A `temp/` subdirectory holds intermediate image files and is deleted after the job.

**Video rendering** (`video_agent.py`): Generates 4 AI images via Pollinations → applies Ken Burns zoom/pan effect alternating per image → builds word-chunk caption overlays with Pillow (no ImageMagick) → composites with MoviePy → muxes voiceover audio → exports 1080×1920 MP4 at 30fps.

**CI/CD**: `.github/workflows/post_shorts.yml` triggers via cron at 02:00, 08:00, 14:00, 20:00 UTC (4 slots). Can also be triggered manually via `workflow_dispatch` with a `slot` input (default `1`). Uploads `result.json`, `seo.json`, and `script.json` as artifacts retained for 30 days.

**Known quirk**: `moviepy==1.0.3` references `Image.ANTIALIAS` which was removed in Pillow 10+; `video_agent.py` patches this with `Image.ANTIALIAS = Image.LANCZOS` at import time.

## Key Config Values (`config.py`)

- `CLAUDE_MODEL = "claude-sonnet-4-6"` — update here to change model for both script and SEO agents
- `VIDEO_WIDTH/HEIGHT = 1080/1920` — YouTube Shorts portrait format
- `VIDEO_FPS = 30`
- Caption styling constants (`CAPTION_FONT_SIZE`, `CAPTION_Y_RATIO`, etc.) live at the top of `video_agent.py`
