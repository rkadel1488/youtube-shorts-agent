# 👶 YT-AGENT: Autonomous YouTube Children's Cartoon Music Engine

An end-to-end autonomous CLI automation engine for generating children's cartoon songs, rendering 1080p animated videos with dynamic camera motion and sing-along subtitles, compiling them into **long-form compilations**, creating **high-CTR 1280x720 cartoon thumbnails**, generating **top-ranking YouTube SEO**, and **auto-publishing** directly to your YouTube channel.

---

## 🌟 Key Features

1. **Persistent Character Creation & Storyboard Generator**:
   - Curated persistent cartoon cast (Barnaby the Bunny, Pip the Duckling, Rexy the Baby Dino, Leo the Lion Cub, Dotti the Elephant).
   - Generates official **Character Specification Cards** (`character_card.png`) and locks character visual tokens across all scenes for persistent 3D animation.
   - Generates multi-scene **Motion Storyboards** (`storyboard.json` and interactive `storyboard.html`) with shot directions, camera motions, and preschool action choreography.

2. **Google Flow & Google Veo 2 Video Generation**:
   - Integrates directly with Google's newest video generation model **Veo 2 (`veo-2.0-generate-001`)** via `@google/genai` using your Google AI Studio API key.
   - Generates real 3D animated motion video clips instead of static pan/zoom images.
   - Built-in **Active Motion Cartoon Synthesizer** fallback featuring rhythmic character bounce synced to the beat, multi-axis camera panning, floating sparkles, and chunky sing-along karaoke subtitle banners.

3. **Trending Copyright-Free Kids Music (124 BPM Preschool Pop)**:
   - Modern, upbeat toddler dance rhythm inspired by YouTube trending nursery hits (Cocomelon, Super Simple Songs, Baby Shark).
   - Features 4-on-the-floor punchy kick, snappy toddler handclaps on 2 and 4, 16th-note shaker sizzle, ukulele offbeat reggae/pop strums, bouncy funk bass, and sparkling glockenspiel earworm melodies.
   - Seamlessly supports external copyright-free MP3/WAV tracks from `assets/audio/trending_music/`.

4. **Long-Form Video Compilation Builder**:
   - Stacks multiple songs (e.g., 3, 5, 8, or 10 songs) into a continuous long-form compilation.
   - Generates animated cartoon bumper cards between songs (*"🎵 Up Next: Five Little Ducks!"*) with audio chime transitions.
   - Automatically calculates exact chapter timestamps down to the second for YouTube search indexing.

5. **High-CTR YouTube Cartoon Thumbnail Generator**:
   - 1280x720 16:9 thumbnails designed for maximum click-through rate in YouTube recommendation feeds.
   - Features giant smiling 3D cartoon character hero (bus, dino, cow, ducks).
   - 3D yellow bubble typography with deep dark outlines, drop shadows, and top ribbon badges (*"⭐ 30 MINS NON-STOP ⭐"*).

6. **Algorithmic YouTube SEO Optimizer**:
   - Click-worthy, keyword-dense titles under 70-90 characters.
   - Rich descriptions containing the **auto-calculated chapter timestamps table** (which triggers Google "Key Moments" in search), full sing-along lyrics for long-tail search indexing, and educational benefit tags.
   - **45+ high-traffic search tags** covering nursery rhymes, preschool learning, toddler sensory, and cartoon songs.
   - Mandatory **COPPA & YouTube Kids compliance flags** (`madeForKids: true`).

7. **Direct YouTube Channel Uploader & OAuth2 Client**:
   - Google YouTube Data API v3 integration with resumable upload streaming.
   - Automatically applies title, description, tags, category (`27` Education), COPPA flag, and attaches the custom 1280x720 thumbnail.

8. **Autopilot Scheduled Cron Runner**:
   - Autonomous background scheduler (`node bin/yt-agent.js autopilot`) that runs on a schedule (e.g., Mon, Wed, Fri at 10 AM).
   - Rotates compilation themes, renders videos, creates thumbnails, and auto-publishes to your channel hands-free.

---

## 🚀 Quick Start

### 1. Run Verification Demo
Test the audio synthesizer, cartoon scene generator, video animator, thumbnail maker, and SEO optimizer in ~25 seconds:
```bash
npm run demo
```

### 2. Generate a Long-Form Compilation
Compile 3 or 5 nursery rhymes into a single long-form video with bumpers, thumbnail, and SEO:
```bash
npm run compile -- -n 3
```

With specific theme and auto-upload:
```bash
npm run compile -- -n 5 -t animals --upload --privacy unlisted
```

### 3. Generate a Single Cartoon Song
```bash
npm run song -- --topic "dino"
```

### 4. Generate High-CTR Cartoon Thumbnails
```bash
npm run thumbnail -- --title "WHEELS ON THE BUS" --badge "⭐ 20 MINS NON-STOP ⭐" --theme bus
```

### 5. Generate High-Ranking YouTube SEO
```bash
npm run seo -- --title "The Wheels on the Bus" --duration "25 Mins"
```

### 6. View Past Generated Compilations
```bash
npm run list
```

---

## 🤖 Autopilot Mode (Scheduled Automation)

Run the autonomous scheduler to generate and publish on a recurring cron schedule:
```bash
# Run on default schedule (Mon, Wed, Fri at 10:00 AM)
npm run autopilot

# Custom schedule (e.g., Every day at 9:00 AM, 5 songs, auto-upload)
npm run autopilot -- -c "0 9 * * *" -n 5 --upload --privacy unlisted
```

---

## 🔐 YouTube Channel Authorization (One-Time Setup)

To enable direct auto-uploading to your YouTube channel:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable the **YouTube Data API v3**.
3. Create **OAuth 2.0 Client IDs** (Application type: *Web application*).
4. Add Authorized redirect URI: `http://localhost:3000/oauth2callback`.
5. Add your `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET` to `.env`.
6. Run the authentication wizard:
   ```bash
   npm run auth
   ```
   *This opens an authorization URL in your browser. Once approved, refresh tokens are securely saved in `credentials/youtube_tokens.json`.*

---

## 📁 Project Structure

```
yt-agent/
├── bin/
│   └── yt-agent.js            # CLI executable entry point
├── src/
│   ├── config/
│   │   ├── index.js           # Settings, video specs, paths
│   │   └── songs_database.js  # Curated nursery rhyme catalog & themes
│   ├── services/
│   │   ├── lyrics/
│   │   │   └── generator.js   # Rhyme generator (Gemini AI + curated templates)
│   │   ├── music/
│   │   │   ├── synthesizer.js # Polyphonic stereo WAV backing track synthesizer
│   │   │   ├── tts_singer.js  # Edge TTS studio vocal singer
│   │   │   └── mixer.js       # Audio mixer, ducking & loudness normalization
│   │   ├── visuals/
│   │   │   ├── scene_generator.js # 1920x1080 3D cartoon vector scenes & AI adapter
│   │   │   └── animator.js    # Ken Burns camera motion & sing-along lyric overlays
│   │   ├── compiler/
│   │   │   └── video_compiler.js # Long-form compilation builder & bumpers
│   │   ├── thumbnail/
│   │   │   └── thumbnail_maker.js # 1280x720 high-CTR cartoon thumbnail designer
│   │   ├── seo/
│   │   │   └── seo_optimizer.js # Titles, chapter descriptions, and 45+ tags
│   │   ├── youtube/
│   │   │   ├── auth.js        # OAuth2 token manager
│   │   │   └── uploader.js    # YouTube Data API v3 direct uploader
│   │   └── autopilot/
│   │       └── scheduler.js   # Autonomous cron background runner
│   └── orchestrator.js        # Master workflow pipeline coordinator
├── output/
│   ├── compilations/          # Master long-form videos & metadata
│   ├── songs/                 # Individual song video clips
│   └── thumbnails/            # High-CTR thumbnails
├── credentials/               # YouTube OAuth token storage
├── logs/                      # Autopilot run logs
├── .env.example
├── package.json
└── README.md
```

---

## 👶 COPPA Compliance Notice
All videos and metadata produced by this workflow automatically include `selfDeclaredMadeForKids: true` and appropriate educational category classifications to fully comply with YouTube Kids policies and the Children's Online Privacy Protection Act (COPPA).
