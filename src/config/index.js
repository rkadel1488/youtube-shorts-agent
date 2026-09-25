const path = require('path');
require('dotenv').config();

const ROOT_DIR = path.resolve(__dirname, '../../');
const DATA_DIR = path.join(ROOT_DIR, 'data');
const ASSETS_DIR = path.join(ROOT_DIR, 'assets');
const OUTPUT_DIR = path.join(ROOT_DIR, 'output');

module.exports = {
  paths: {
    root: ROOT_DIR,
    data: DATA_DIR,
    assets: ASSETS_DIR,
    output: OUTPUT_DIR,
    compilations: path.join(OUTPUT_DIR, 'compilations'),
    songs: path.join(OUTPUT_DIR, 'songs'),
    thumbnails: path.join(OUTPUT_DIR, 'thumbnails'),
    temp: path.join(ROOT_DIR, 'temp'),
    credentials: path.join(ROOT_DIR, 'credentials')
  },
  video: {
    width: 1920,
    height: 1080,
    fps: 30,
    bitrate: '4500k',
    audioBitrate: '192k',
    defaultCompilationSongCount: 5,
    transitionDurationSec: 2.0,
    bumperDurationSec: 3.5
  },
  thumbnail: {
    width: 1280,
    height: 720
  },
  audio: {
    sampleRate: 44100,
    defaultBpm: 115,
    defaultVoice: 'en-US-AnaNeural', // Playful child voice
    voiceOptions: [
      { id: 'en-US-AnaNeural', name: 'Ana (Playful Child / Toddler)', pitch: '+12Hz', rate: '+5%' },
      { id: 'en-US-JennyNeural', name: 'Jenny (Warm Teacher / Mom)', pitch: '+5Hz', rate: '+0%' },
      { id: 'en-US-ChristopherNeural', name: 'Christopher (Cheerful Storyteller)', pitch: '+4Hz', rate: '+0%' },
      { id: 'en-GB-SoniaNeural', name: 'Sonia (British Joyful Narrator)', pitch: '+8Hz', rate: '+2%' }
    ]
  },
  youtube: {
    clientId: process.env.YOUTUBE_CLIENT_ID || '',
    clientSecret: process.env.YOUTUBE_CLIENT_SECRET || '',
    redirectUri: process.env.YOUTUBE_REDIRECT_URI || 'http://localhost:3000/oauth2callback',
    tokenPath: path.join(ROOT_DIR, 'credentials', 'youtube_tokens.json'),
    channelId: process.env.YOUTUBE_CHANNEL_ID || '',
    categoryId: '27', // 27 = Education, 24 = Entertainment
    defaultPrivacy: process.env.YOUTUBE_PRIVACY || 'unlisted', // 'private', 'unlisted', 'public'
    madeForKids: true // Mandatory COPPA compliance for children content
  },
  ai: {
    geminiApiKey: process.env.GEMINI_API_KEY || process.env.GOOGLE_AI_STUDIO_API_KEY || '',
    anthropicApiKey: process.env.ANTHROPIC_API_KEY || '',
    openaiApiKey: process.env.OPENAI_API_KEY || '',
    replicateApiToken: process.env.REPLICATE_API_TOKEN || ''
  },
  autopilot: {
    schedule: process.env.AUTOPILOT_CRON || '0 10 * * 1,3,5', // Default: 10 AM Mon, Wed, Fri
    autoPublish: process.env.AUTOPILOT_AUTO_PUBLISH === 'true'
  }
};
