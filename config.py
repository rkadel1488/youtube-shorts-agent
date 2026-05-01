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

# Posting schedule — 5 slots per day (00:00, 05:00, 10:00, 15:00, 20:00 UTC by default)
POSTING_TIMES: list[str] = os.getenv("POSTING_TIMES", "00:00,05:00,10:00,15:00,20:00").split(",")

# Video output settings
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

# Claude model
CLAUDE_MODEL = "claude-sonnet-4-6"

# Niche rotation — 4 niches, 2 shorts/day, cycling daily
NICHES = [
    {
        "name": "facts_mystery",
        "label": "Facts & Mystery",
        "category_id": "27",  # Education
        "search_terms": ["mystery", "ancient", "secret", "enigma", "discovery"],
    },
    {
        "name": "storytelling",
        "label": "Storytelling",
        "category_id": "24",  # Entertainment
        "search_terms": ["story", "narrative", "drama", "emotion", "character"],
    },
    {
        "name": "animated_stories",
        "label": "Animated Stories",
        "category_id": "1",   # Film & Animation
        "search_terms": ["animation", "fantasy", "colorful", "magic", "cartoon"],
    },
    {
        "name": "travel_culture",
        "label": "Travel & Culture",
        "category_id": "19",  # Travel & Events
        "search_terms": ["travel", "culture", "landscape", "architecture", "destination"],
    },
]

MADE_FOR_KIDS: bool = os.getenv("MADE_FOR_KIDS", "false").lower() == "true"
