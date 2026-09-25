# 👶 YT-AGENT: Autonomous YouTube Children's Cartoon Music Engine

An end-to-end autonomous CLI automation engine for generating children's cartoon songs, rendering 1080p animated videos with dynamic camera motion and sing-along subtitles, compiling them into **long-form compilations**, creating **high-CTR 1280x720 cartoon thumbnails**, generating **top-ranking YouTube SEO**, and **auto-publishing** directly to your YouTube channel.

---

## 🌟 Key Features

1. **Catchy Song & Lyrics Generation**:
   - Curated catalog of toddler favorites (*The Wheels on the Bus*, *Old MacDonald's Farm*, *Baby Dino Stomp*, *Colors of the Rainbow*, *Five Little Ducks*, *Twinkle Twinkle*, and *Alphabet Safari*).
   - Generates rhyming, repetitive, rhythmic verse structures designed for toddler retention and parent sing-alongs.
   - Optional AI integration via Google Gemini API for infinite dynamic song generation.

2. **Studio Vocal Singer & Polyphonic Nursery Music**:
   - **Zero subscription cost**: Powered by Microsoft Edge Speech engine (`msedge-tts`) producing clear children's cartoon voices (Ana, Jenny, Christopher, Sonia).
   - Polyphonic instrumental synthesizer generates cheerful glockenspiel chimes, bouncy basslines, and toddler handclaps in major nursery scales.
   - Built-in automatic vocal ducking (-2.5 dB) and YouTube EBU R128 loudness normalization (-14 LUFS target).

3. **1080p 3D Cartoon Animations**:
   - High-saturation, Pixar/Cocomelon-style 1920x1080 cartoon scenes (sunny hills, red farm barns, friendly dinosaurs, underwater ponds, magical starry skies).
   - Ken Burns dynamic camera motion (smooth zoom-in, pan left/right, cartoon rhythm bounce).
   - High-contrast sing-along bubble subtitle banners with deep cartoon outlines (`#1A0033`, 14px stroke) ensuring 100% readability.

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
