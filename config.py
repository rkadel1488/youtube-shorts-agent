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

# Niche rotation — 6 niches, cycling daily across 5 slots
NICHES = [
    {
        "name": "cricket",
        "label": "Cricket",
        "category_id": "17",  # Sports
        "search_terms": ["cricket", "stadium", "batting", "bowling", "match"],
    },
    {
        "name": "history",
        "label": "History",
        "category_id": "27",  # Education
        "search_terms": ["ancient", "war", "empire", "civilization", "historical"],
    },
    {
        "name": "facts",
        "label": "Amazing Facts",
        "category_id": "27",  # Education
        "search_terms": ["science", "space", "nature", "discovery", "universe"],
    },
    {
        "name": "horror",
        "label": "Horror",
        "category_id": "24",  # Entertainment
        "search_terms": ["dark", "haunted", "mystery", "eerie", "shadow"],
    },
    {
        "name": "anime",
        "label": "Anime",
        "category_id": "1",   # Film & Animation
        "search_terms": ["anime", "manga", "japan", "animation", "character"],
    },
    {
        "name": "movies",
        "label": "Movies",
        "category_id": "24",  # Entertainment
        "search_terms": ["cinema", "film", "hollywood", "actor", "movie"],
    },
]

MADE_FOR_KIDS: bool = os.getenv("MADE_FOR_KIDS", "false").lower() == "true"

# 90 pre-defined storylines (15 per niche) — script_agent picks one randomly each run
STORY_TOPICS: dict[str, list[str]] = {
    "cricket": [
        "The match where one bowler took all 10 wickets alone",
        "The batsman who scored a century on debut and was never picked again",
        "The blind cricketer who played international matches",
        "The greatest umpiring controversy — the catch that was never out",
        "The cricket ball that killed a batsman and changed the rules forever",
        "The team that won a World Cup with 11 players nobody had heard of",
        "The player who represented two rival nations in the same tournament",
        "The match secretly fixed to help the opposing team win",
        "6 sixes in one over — the moment that broke cricket records forever",
        "The cricketer who faked his death to escape a match-fixing scandal",
        "The fastest ball ever bowled — and the batsman who hit it for six",
        "The last-ball finish that gave a nation its very first World Cup",
        "The fielder who dropped the catch that lost the Ashes for his country",
        "The spinner who dismissed every great batsman with a single delivery style",
        "The cricket match played during a war that made both sides stop fighting",
    ],
    "history": [
        "The letter written by a teenager that accidentally started World War I",
        "The Roman emperor who officially declared war on the ocean",
        "The city buried alive and perfectly preserved for 2000 years",
        "The woman who single-handedly stopped an entire invading army",
        "The soldier still fighting World War II 29 years after it ended",
        "The assassination that almost didn't happen — three failed attempts in one day",
        "The ancient civilization that vanished overnight without a single trace",
        "The ancient map that revealed a 500-year-old conspiracy",
        "The plague that wiped out half of Europe in just three years",
        "The king so feared his name was erased from every record in history",
        "The year the sun went dark for 18 months and millions starved",
        "The invention stolen, patented, and used to make someone else a billionaire",
        "The battle where 300 soldiers defeated an army of one million",
        "The secret tunnel under the Berlin Wall that freed 57 people in one night",
        "The dictator brought down by secrets hidden inside his own diary",
    ],
    "facts": [
        "Your body replaces itself completely every 7 years — every cell, gone",
        "The real reason you can't remember being a baby — and it's terrifying",
        "The color that doesn't exist — but your brain creates it anyway",
        "Cleopatra lived closer to the Moon landing than to the pyramids",
        "The ant colony that has been alive and running for 100 million years",
        "Your phone has more computing power than NASA used to reach the Moon",
        "The ocean is so deep that Mount Everest would vanish completely inside it",
        "Honey found in Egyptian tombs is still perfectly edible after 3000 years",
        "The loudest sound in history was heard 5000 kilometers away",
        "A single day on Venus is longer than an entire year on Venus",
        "Trees communicate with each other through secret underground fungal networks",
        "The human eye can spot a single candle flame from 48 kilometers away",
        "Sharks existed 200 million years before the first tree ever grew on Earth",
        "You share 60% of your DNA with a banana — and scientists can prove it",
        "The Great Wall of China cannot be seen from space — it was never true",
    ],
    "horror": [
        "The hotel room sealed shut for 30 years after a guest vanished inside it",
        "The doll that blinks on its own — and no one in the house is moving it",
        "The town where every child drew the exact same nightmare for 40 years",
        "The man who woke up at his own funeral — and no one believed him",
        "The voice recording found in an abandoned asylum that answered questions",
        "The twin who felt every injury her sister suffered from 3000 miles away",
        "The lighthouse keeper's last log entry — written after he officially died",
        "The forest where no animal has willingly entered in over 100 years",
        "The painting that shows a completely different person every time you photograph it",
        "The apartment where 11 tenants vanished — all on the same day of the month",
        "The child who described her previous death in exact forensic detail",
        "The clock that stopped at the precise moment its owner died — every generation",
        "The Victorian mirror found in a sealed room showing a room that doesn't exist",
        "The surgeon who operated on himself and found something inside he couldn't explain",
        "The phone call received from a number disconnected 20 years earlier",
    ],
    "anime": [
        "The anime that predicted a major world disaster — aired one month before",
        "The character death that triggered a national crisis across all of Japan",
        "The anime banned in 30 countries because of a single scene",
        "The creator who secretly put his own trauma into every single episode",
        "The villain who was right all along — and fans only realized it too late",
        "The anime studio that went bankrupt the very day their masterpiece released",
        "The opening theme that contains a hidden message when played backwards",
        "The character meant to die in episode 1 — kept alive by fan outcry",
        "The anime considered a total flop that became the biggest franchise ever",
        "The real Japanese city that sued an anime for destroying its reputation",
        "The episode so disturbing it triggered mass seizures across multiple countries",
        "The mangaka who hand-drew 10000 pages before anyone read a single one",
        "The anime that correctly predicted a major scientific discovery 10 years early",
        "The final episode twist that broke the internet before the internet existed",
        "The side character fans loved more than the hero — who got their own series",
    ],
    "movies": [
        "The movie set so cursed that three actors died during production",
        "The accidental improvised scene that became the most iconic moment in cinema",
        "The film rejected by every single studio that went on to make 4 billion dollars",
        "The actor who stayed in character for 3 full years and lost their mind",
        "The movie banned for 25 years that is now studied in film universities",
        "The director who secretly filmed the entire movie without telling the cast",
        "The child actor who sued the studio for stealing their entire childhood salary",
        "The real event so horrifying Hollywood refused to film it for 40 years",
        "The deleted scene that would have completely changed the ending everyone loves",
        "The movie that accidentally predicted a major world event with perfect accuracy",
        "The special effects so realistic the FBI opened a criminal investigation",
        "The Oscar winner who threw their award in the trash the very next morning",
        "The sequel so bad it was legally erased from existence by court order",
        "The voice actor who voiced 27 different characters in the same film undetected",
        "The audience that rioted inside cinemas on opening night — and exactly why",
    ],
}

