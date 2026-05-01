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
GEMINI_TTS_VOICE: str = os.getenv("GEMINI_TTS_VOICE", "Charon")

# YouTube OAuth files
YOUTUBE_CLIENT_SECRETS_FILE: str = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")
YOUTUBE_TOKEN_FILE: str = os.getenv("YOUTUBE_TOKEN_FILE", "youtube_token.json")
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Posting schedule
POSTING_TIMES: list[str] = os.getenv("POSTING_TIMES", "08:00,18:00").split(",")

# Video output settings
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

# Claude model
CLAUDE_MODEL = "claude-sonnet-4-6"

# Niche rotation — 5 niches, 2 shorts/day, cycling daily
NICHES = [
    {
        "name": "dark_psychology",
        "label": "Dark Psychology",
        "category_id": "27",  # Education
        "search_terms": ["psychology", "mind", "brain", "people", "behavior"],
    },
    {
        "name": "ai_tools",
        "label": "AI Tools",
        "category_id": "28",  # Science & Technology
        "search_terms": ["technology", "computer", "robot", "digital", "screen"],
    },
    {
        "name": "history_facts",
        "label": "History Facts",
        "category_id": "27",
        "search_terms": ["ancient", "history", "ruins", "map", "civilization"],
    },
    {
        "name": "money_secrets",
        "label": "Money Secrets",
        "category_id": "27",
        "search_terms": ["money", "business", "finance", "investment", "wealth"],
    },
    {
        "name": "space_universe",
        "label": "Space & Universe",
        "category_id": "28",
        "search_terms": ["space", "galaxy", "stars", "universe", "cosmos"],
    },
]

MADE_FOR_KIDS: bool = os.getenv("MADE_FOR_KIDS", "false").lower() == "true"
