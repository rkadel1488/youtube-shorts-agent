const config = require('../../config');
const { SONGS_DATABASE, getSongById, getRandomSongs } = require('../../config/songs_database');
const fs = require('fs');
const path = require('path');
const axios = require('axios');

// Load 100 Kids Educational Topics extracted from user repository
const KIDS_TOPICS_PATH = path.join(__dirname, '../../config/kids_topics.json');
let KIDS_TOPICS = [];
if (fs.existsSync(KIDS_TOPICS_PATH)) {
  try {
    KIDS_TOPICS = JSON.parse(fs.readFileSync(KIDS_TOPICS_PATH, 'utf8'));
  } catch (e) {}
}

/**
 * Lyrics & Song Script Generator for Children's Cartoons
 * Supports:
 * - 100 Children's Educational Topics (Animals, Colours, Numbers, Space, Feelings)
 * - Google Gemini API (via GOOGLE_AI_STUDIO_API_KEY or GEMINI_API_KEY)
 * - Anthropic Claude API (via ANTHROPIC_API_KEY)
 * - Curated Offline Nursery Rhymes Catalog (Zero Cost / Zero Key Fallback)
 */
class LyricsGenerator {
  constructor() {
    this.geminiApiKey = config.ai.geminiApiKey;
    this.anthropicApiKey = config.ai.anthropicApiKey;
    this.kidsTopics = KIDS_TOPICS;
  }

  /**
   * Returns the list of 100 kids educational topics
   */
  getKidsTopics() {
    return this.kidsTopics;
  }

  /**
   * Generate or retrieve a song by topic, topicId, or songId
   * @param {Object} options { topic, topicId, songId, customPrompt }
   */
  async generateSong(options = {}) {
    const { topic, topicId, songId, customPrompt } = options;

    // 1. If explicit songId is provided from nursery database
    if (songId) {
      const dbSong = getSongById(songId);
      if (dbSong) return JSON.parse(JSON.stringify(dbSong));
    }

    // 2. If topicId is provided (1-100 from kids_topics.json)
    let selectedTopic = topic;
    let selectedPremise = '';
    if (topicId && this.kidsTopics.length > 0) {
      const found = this.kidsTopics.find(t => t.id === parseInt(topicId));
      if (found) {
        selectedTopic = found.title;
        selectedPremise = found.premise;
      }
    }

    // 3. If Claude API Key is available, use Claude (from user's original repo)
    if (this.anthropicApiKey && (selectedTopic || customPrompt)) {
      try {
        const claudeSong = await this._generateWithClaude(selectedTopic || customPrompt, selectedPremise);
        if (claudeSong && claudeSong.verses && claudeSong.verses.length > 0) {
          return claudeSong;
        }
      } catch (err) {
        console.warn(`[LyricsGenerator] Claude API generation error: ${err.message}. Trying Gemini/Templates.`);
      }
    }

    // 4. If Gemini API Key is available, use Gemini
    if (this.geminiApiKey && (selectedTopic || customPrompt)) {
      try {
        const geminiSong = await this._generateWithGemini(selectedTopic || customPrompt, selectedPremise);
        if (geminiSong && geminiSong.verses && geminiSong.verses.length > 0) {
          return geminiSong;
        }
      } catch (err) {
        console.warn(`[LyricsGenerator] Gemini API generation error: ${err.message}. Falling back to curated templates.`);
      }
    }

    // 5. Fallback: match by topic keyword from database or pick random
    if (selectedTopic) {
      const topicLower = selectedTopic.toLowerCase();
      const matched = SONGS_DATABASE.find(s => 
        s.theme.toLowerCase().includes(topicLower) || 
        s.title.toLowerCase().includes(topicLower) ||
        s.seoKeywords.some(k => k.toLowerCase().includes(topicLower))
      );
      if (matched) return JSON.parse(JSON.stringify(matched));
    }

    // Default: Return random song from curated database
    const randomList = getRandomSongs(1);
    return JSON.parse(JSON.stringify(randomList[0]));
  }

  /**
   * Generates a compilation playlist of songs
   * @param {number} count Number of songs
   * @param {string} themeCategory Optional theme filter
   */
  async generateCompilationPlaylist(count = 5, themeCategory = null) {
    let pool = [...SONGS_DATABASE];
    if (themeCategory) {
      const filtered = pool.filter(s => s.theme === themeCategory);
      if (filtered.length >= count) {
        pool = filtered;
      }
    }

    const shuffled = pool.sort(() => 0.5 - Math.random());
    const selected = shuffled.slice(0, Math.min(count, pool.length));

    while (selected.length < count) {
      const baseSong = pool[selected.length % pool.length];
      const clone = JSON.parse(JSON.stringify(baseSong));
      clone.id = `${clone.id}-part-${selected.length + 1}`;
      clone.title = `${clone.title} (Sing-Along Edition)`;
      selected.push(clone);
    }

    return selected;
  }

  /**
   * Generates song via Anthropic Claude API
   */
  async _generateWithClaude(topic, premise = '') {
    const prompt = this._buildSongPrompt(topic, premise);
    const url = 'https://api.anthropic.com/v1/messages';

    const response = await axios.post(url, {
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 2000,
      system: 'You are a master children\'s songwriter and preschool educator creating viral Cocomelon / Super Simple Songs style nursery rhymes. Output valid JSON only, no markdown formatting or fences.',
      messages: [{ role: 'user', content: prompt }]
    }, {
      headers: {
        'x-api-key': this.anthropicApiKey,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
      },
      timeout: 25000
    });

    const text = response.data?.content?.[0]?.text;
    const cleanJson = text.replace(/```json/g, '').replace(/```/g, '').trim();
    return JSON.parse(cleanJson);
  }

  /**
   * Generates song via Google Gemini API
   */
  async _generateWithGemini(topic, premise = '') {
    const prompt = this._buildSongPrompt(topic, premise);
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${this.geminiApiKey}`;

    const response = await axios.post(url, {
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: {
        responseMimeType: 'application/json'
      }
    }, { timeout: 20000 });

    const rawText = response.data?.candidates?.[0]?.content?.parts?.[0]?.text;
    if (rawText) {
      return JSON.parse(rawText);
    }
    throw new Error('Empty response from Gemini API');
  }

  _buildSongPrompt(topic, premise) {
    return `
Create a viral, catchy, 3D cartoon preschool nursery rhyme for toddlers and children.
Topic: "${topic}"
${premise ? `Story/Premise Context: "${premise}"` : ''}

Rules:
1. Write 3 to 4 repetitive, rhythmic, rhyming verses that toddlers can easily sing along to.
2. Positive educational focus (animal sounds, colors, numbers, laughter, kindness).
3. For each verse, provide a vivid 1920x1080 3D cartoon scene visual description (Pixar/Cocomelon style character, smiling, bright lighting).

Output ONLY valid JSON matching this schema:
{
  "id": "generated-song-slug",
  "title": "${topic}",
  "subtitle": "Fun Toddler Sing-Along",
  "theme": "kids_learning",
  "bpm": 115,
  "musicalStyle": "bounce",
  "mood": "upbeat, joyful, bouncy",
  "characterHero": "cute cartoon animal or character description",
  "colorPalette": {
    "sky": ["#4FC3F7", "#B3E5FC"],
    "ground": ["#81C784", "#4CAF50"],
    "primary": "#FFD54F",
    "accent": "#FF7043"
  },
  "verses": [
    {
      "verseNumber": 1,
      "lyrics": "Rhyming verse text here",
      "sceneDescription": "Detailed 3D cartoon scene visual description"
    }
  ],
  "seoKeywords": ["nursery rhymes", "kids songs", "${topic.toLowerCase()}"]
}
`;
  }
}

module.exports = new LyricsGenerator();
