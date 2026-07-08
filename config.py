import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
# Only load .env if running locally (GitHub Actions sets secrets as real env vars)
if not os.getenv("GITHUB_ACTIONS"):
    load_dotenv(BASE_DIR / ".env", override=True)
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# API keys
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_AI_STUDIO_API_KEY: str = os.getenv("GOOGLE_AI_STUDIO_API_KEY", "")
PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY", "")

# Gemini TTS voice — options: Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede
GEMINI_TTS_VOICE: str = os.getenv("GEMINI_TTS_VOICE", "Puck")

# YouTube OAuth files
YOUTUBE_CLIENT_SECRETS_FILE: str = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")
YOUTUBE_TOKEN_FILE: str = os.getenv("YOUTUBE_TOKEN_FILE", "youtube_token.json")
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Posting schedule — 4 slots per day (02:00, 08:00, 14:00, 20:00 UTC by default)
POSTING_TIMES: list[str] = os.getenv("POSTING_TIMES", "00:00,08:00,16:00").split(",")

# Video output settings
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

# Claude model
CLAUDE_MODEL = "claude-sonnet-4-6"

MADE_FOR_KIDS: bool = os.getenv("MADE_FOR_KIDS", "false").lower() == "true"

# Default YouTube category for uploads (22 = People & Blogs)
YOUTUBE_CATEGORY_ID: str = os.getenv("YOUTUBE_CATEGORY_ID", "22")

