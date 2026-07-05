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
| `POSTING_TIMES` | Comma-separated HH:MM times, default `02:00,08:00,14:00,20:00` (4 slots/day) |
| `MADE_FOR_KIDS` | `true`/`false`, default `false` |

## Architecture

The system is a linear 5-step pipeline orchestrated by `main.py::run_pipeline()`. Each step is an independent agent module:

```
main.py::run_pipeline()
  ├─ agents/trend_agent.py   → trends/evergreen → {title, premise, hook_angle}
  ├─ agents/script_agent.py  → Claude API → {topic, hook, script, keywords}
  ├─ agents/seo_agent.py     → Claude API → {title, description, tags, hashtags}
  ├─ agents/audio_agent.py   → Gemini TTS → voiceover.mp3
  ├─ agents/video_agent.py   → Pollinations FLUX (via image_agent) + MoviePy → final.mp4
  │    └─ agents/image_agent.py  → Pollinations.ai free API → 4 × scene_XX.jpg
  └─ agents/upload_agent.py  → YouTube Data API v3 → video ID
```

Each agent function signature is simple and self-contained — they receive plain Python types and return a path or dict. All agents implement a `retries` loop with exponential backoff.

**Topics**: `agents/trend_agent.py::get_trend_topic()` fetches live trending topics from the Google Trends daily RSS (including attached real news headlines/snippets) and Reddit r/popular (both keyless), then Claude picks the safest/strongest candidate and writes a factual premise grounded ONLY in those headlines. Topics are deduped against `state/history.json`. If all trend sources fail, `get_evergreen_topic()` generates a well-established-facts topic instead, so a scheduled run never fails for lack of a topic. Scripts always go through `script_agent.generate_trend_script()` — a factual explainer template that forbids inventing facts beyond the premise. `TREND_REGION` (default `US`) sets the Google Trends geo.

**Output layout**: Each job writes to `output/<timestamp>_slot<N>/` containing `script.json`, `seo.json`, `final.mp4`, and `result.json`. A `temp/` subdirectory holds intermediate image/voiceover files and is deleted after the job.

**Video rendering** (`video_agent.py`): Generates 4 AI images via Pollinations → applies Ken Burns zoom/pan effect alternating per image → builds word-chunk caption overlays with Pillow (no ImageMagick) → composites with MoviePy → muxes voiceover audio → exports 1080×1920 MP4 at 30fps.

**CI/CD**: `.github/workflows/post_shorts.yml` triggers via cron at 02:00, 08:00, 14:00, 20:00 UTC (4 slots). Can also be triggered manually via `workflow_dispatch` with a `slot` input (default `1`). Uploads `result.json`, `seo.json`, and `script.json` as artifacts retained for 30 days.

**Known quirk**: `moviepy==1.0.3` references `Image.ANTIALIAS` which was removed in Pillow 10+; `video_agent.py` patches this with `Image.ANTIALIAS = Image.LANCZOS` at import time.

## Key Config Values (`config.py`)

- `CLAUDE_MODEL = "claude-sonnet-4-6"` — update here to change model for both script and SEO agents
- `VIDEO_WIDTH/HEIGHT = 1080/1920` — YouTube Shorts portrait format
- `VIDEO_FPS = 30`
- Caption styling constants (`CAPTION_FONT_SIZE`, `CAPTION_Y_RATIO`, etc.) live at the top of `video_agent.py`
