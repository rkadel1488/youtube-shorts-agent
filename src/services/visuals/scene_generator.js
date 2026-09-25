const sharp = require('sharp');
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const config = require('../../config');

/**
 * 3D Cartoon Scene Visual Generator for Children's Nursery Rhymes
 * Generates vibrant, high-saturation, Pixar/Cocomelon aesthetic 1920x1080 cartoon scenes.
 * Features built-in procedural vector engine (zero cost) + optional AI generation adapter.
 */
class SceneGenerator {
  constructor() {
    this.width = config.video.width || 1920;
    this.height = config.video.height || 1080;
  }

  /**
   * Generates a 1920x1080 cartoon scene image for a song verse
   * @param {Object} verse Verse details { lyrics, sceneDescription, verseNumber }
   * @param {Object} song Song details { id, theme, title, colorPalette }
   * @param {string} outputPath Destination path (.png)
   */
  async generateScene(verse, song, outputPath) {
    const dir = path.dirname(outputPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    // 1. If OpenAI DALL-E 3 is configured and user enabled AI images
    if (config.ai.openaiApiKey && process.env.USE_AI_IMAGES === 'true') {
      try {
        const aiUrl = await this._generateWithDalle(verse.sceneDescription || song.title);
        const imgBuffer = (await axios.get(aiUrl, { responseType: 'arraybuffer' })).data;
        await sharp(imgBuffer).resize(this.width, this.height).png().toFile(outputPath);
        return outputPath;
      } catch (err) {
        console.warn(`[SceneGenerator] AI image generation warning: ${err.message}. Using high-res procedural cartoon engine.`);
      }
    }

    // 2. High-Fidelity Procedural 3D Cartoon Scene Synthesizer (Zero Cost & Fast)
    const svgContent = this._buildProceduralCartoonSvg(verse, song);
    await sharp(Buffer.from(svgContent))
      .resize(this.width, this.height)
      .png({ quality: 95 })
      .toFile(outputPath);

    return outputPath;
  }

  /**
   * Builds rich, layered 1920x1080 cartoon SVG matching the song theme
   */
  _buildProceduralCartoonSvg(verse, song) {
    const theme = (song.theme || '').toLowerCase();
    const verseNum = verse.verseNumber || 1;

    let sceneLayers = '';

    if (theme.includes('vehicle') || song.id.includes('bus')) {
      sceneLayers = this._themeBusRoad(verseNum);
    } else if (theme.includes('farm') || theme.includes('animal') || song.id.includes('macdonald')) {
      sceneLayers = this._themeFarmAnimals(verseNum);
    } else if (theme.includes('dino')) {
      sceneLayers = this._themeDinosaurJungle(verseNum);
    } else if (theme.includes('color') || theme.includes('rainbow')) {
      sceneLayers = this._themeRainbowColors(verseNum);
    } else if (theme.includes('duck') || theme.includes('count')) {
      sceneLayers = this._themeDuckPond(verseNum);
    } else if (theme.includes('bedtime') || theme.includes('lullaby') || theme.includes('star')) {
      sceneLayers = this._themeBedtimeLullaby(verseNum);
    } else if (theme.includes('alphabet')) {
      sceneLayers = this._themeAlphabetSafari(verseNum);
    } else {
      sceneLayers = this._themePlaygroundCelebration(verseNum);
    }

    return `
<svg xmlns="http://www.w3.org/2000/svg" width="${this.width}" height="${this.height}" viewBox="0 0 ${this.width} ${this.height}">
  <defs>
    <!-- Sky Gradient -->
    <linearGradient id="skyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#4FC3F7" />
      <stop offset="55%" stop-color="#B3E5FC" />
      <stop offset="100%" stop-color="#E1F5FE" />
    </linearGradient>

    <!-- Sun Glow -->
    <radialGradient id="sunGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#FFF176" stop-opacity="1" />
      <stop offset="70%" stop-color="#FFEE58" stop-opacity="0.8" />
      <stop offset="100%" stop-color="#FDD835" stop-opacity="0" />
    </radialGradient>

    <!-- Hill Gradients -->
    <linearGradient id="hillGrad1" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#81C784" />
      <stop offset="100%" stop-color="#388E3C" />
    </linearGradient>
    <linearGradient id="hillGrad2" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#AED581" />
      <stop offset="100%" stop-color="#689F38" />
    </linearGradient>

    <!-- Soft Drop Shadow Filter -->
    <filter id="softShadow" x="-10%" y="-10%" width="130%" height="130%">
      <feDropShadow dx="0" dy="12" stdDeviation="12" flood-color="#000000" flood-opacity="0.25" />
    </filter>
    <filter id="heroShadow" x="-15%" y="-15%" width="130%" height="130%">
      <feDropShadow dx="0" dy="16" stdDeviation="14" flood-color="#000000" flood-opacity="0.32" />
    </filter>
  </defs>

  ${sceneLayers}
</svg>
    `;
  }

  // --- THEME 1: WHEELS ON THE BUS ---
  _themeBusRoad(verseNum) {
    const busPositions = [
      { x: 560, y: 520, scale: 1.0 },
      { x: 500, y: 530, scale: 1.05 },
      { x: 620, y: 510, scale: 0.98 },
      { x: 550, y: 525, scale: 1.02 }
    ];
    const pos = busPositions[(verseNum - 1) % busPositions.length];

    return `
  <!-- Sky -->
  <rect width="1920" height="1080" fill="url(#skyGrad)" />

  <!-- Smiling Sun -->
  <circle cx="240" cy="220" r="140" fill="url(#sunGlow)" />
  <circle cx="240" cy="220" r="80" fill="#FDD835" />
  <ellipse cx="215" cy="210" rx="9" ry="14" fill="#3E2723" />
  <ellipse cx="265" cy="210" rx="9" ry="14" fill="#3E2723" />
  <circle cx="218" cy="205" r="4" fill="#FFFFFF" />
  <circle cx="268" cy="205" r="4" fill="#FFFFFF" />
  <circle cx="195" cy="225" r="12" fill="#FF8A80" opacity="0.6" />
  <circle cx="285" cy="225" r="12" fill="#FF8A80" opacity="0.6" />
  <path d="M 215 230 Q 240 260 265 230" stroke="#3E2723" stroke-width="7" stroke-linecap="round" fill="none" />

  <!-- Clouds -->
  <g fill="#FFFFFF" opacity="0.95">
    <circle cx="580" cy="180" r="60" /><circle cx="640" cy="160" r="75" /><circle cx="710" cy="175" r="60" />
    <circle cx="1450" cy="220" r="70" /><circle cx="1520" cy="190" r="85" /><circle cx="1600" cy="210" r="70" />
  </g>

  <!-- Rolling Green Hills -->
  <path d="M -100 700 Q 400 480 950 670 T 2020 620 L 2020 1080 L -100 1080 Z" fill="url(#hillGrad1)" filter="url(#softShadow)" />
  <path d="M -100 800 Q 550 640 1150 800 T 2020 740 L 2020 1080 L -100 1080 Z" fill="url(#hillGrad2)" />

  <!-- Road -->
  <path d="M -50 940 Q 960 900 2000 950 L 2000 1080 L -50 1080 Z" fill="#607D8B" />
  <path d="M 0 1010 Q 960 990 1920 1010" stroke="#FFFFFF" stroke-width="14" stroke-dasharray="60 40" fill="none" />

  <!-- Cartoon Bus Hero -->
  <g transform="translate(${pos.x}, ${pos.y}) scale(${pos.scale})" filter="url(#heroShadow)">
    <rect x="0" y="0" width="800" height="380" rx="60" fill="#FDD835" stroke="#E65100" stroke-width="12" />
    <rect x="0" y="220" width="800" height="35" fill="#E53935" />

    <!-- Windows -->
    <rect x="50" y="50" width="180" height="140" rx="25" fill="#E0F7FA" stroke="#37474F" stroke-width="8" />
    <rect x="260" y="50" width="150" height="140" rx="25" fill="#E0F7FA" stroke="#37474F" stroke-width="8" />
    <rect x="440" y="50" width="150" height="140" rx="25" fill="#E0F7FA" stroke="#37474F" stroke-width="8" />
    <rect x="620" y="50" width="140" height="140" rx="25" fill="#E0F7FA" stroke="#37474F" stroke-width="8" />

    <!-- Smiling Bus Face -->
    <ellipse cx="110" cy="120" rx="18" ry="26" fill="#263238" />
    <ellipse cx="170" cy="120" rx="18" ry="26" fill="#263238" />
    <circle cx="115" cy="112" r="7" fill="#FFFFFF" />
    <circle cx="175" cy="112" r="7" fill="#FFFFFF" />
    <ellipse cx="85" cy="145" rx="16" ry="10" fill="#FF8A80" opacity="0.7" />
    <ellipse cx="195" cy="145" rx="16" ry="10" fill="#FF8A80" opacity="0.7" />
    <path d="M 125 140 Q 140 165 155 140" stroke="#263238" stroke-width="7" stroke-linecap="round" fill="#E53935" />

    <!-- Cheerful Animals in Windows -->
    <!-- Bear in Window 2 -->
    <circle cx="335" cy="120" r="38" fill="#8D6E63" />
    <circle cx="315" cy="90" r="14" fill="#6D4C41" /><circle cx="355" cy="90" r="14" fill="#6D4C41" />
    <circle cx="325" cy="115" r="5" fill="#000000" /><circle cx="345" cy="115" r="5" fill="#000000" />
    <!-- Bunny in Window 3 -->
    <ellipse cx="500" cy="75" rx="10" ry="30" fill="#FFFFFF" /><ellipse cx="530" cy="75" rx="10" ry="30" fill="#FFFFFF" />
    <circle cx="515" cy="125" r="36" fill="#FFFFFF" />
    <circle cx="505" cy="120" r="4" fill="#000000" /><circle cx="525" cy="120" r="4" fill="#000000" />
    <!-- Monkey in Window 4 -->
    <circle cx="690" cy="125" r="35" fill="#A1887F" />
    <circle cx="660" cy="125" r="12" fill="#FFCCBC" /><circle cx="720" cy="125" r="12" fill="#FFCCBC" />
    <circle cx="680" cy="120" r="5" fill="#000000" /><circle cx="700" cy="120" r="5" fill="#000000" />

    <!-- Wheels -->
    <g transform="translate(160, 360)">
      <circle cx="0" cy="0" r="70" fill="#263238" /><circle cx="0" cy="0" r="45" fill="#B0BEC5" stroke="#78909C" stroke-width="8" /><circle cx="0" cy="0" r="20" fill="#ECEFF1" />
    </g>
    <g transform="translate(640, 360)">
      <circle cx="0" cy="0" r="70" fill="#263238" /><circle cx="0" cy="0" r="45" fill="#B0BEC5" stroke="#78909C" stroke-width="8" /><circle cx="0" cy="0" r="20" fill="#ECEFF1" />
    </g>
  </g>

  <!-- Floating Music Notes & Sparkles -->
  <text x="380" y="420" font-size="70" font-weight="bold" fill="#FF4081" stroke="#880E4F" stroke-width="2">♪</text>
  <text x="1480" y="460" font-size="85" font-weight="bold" fill="#00E676" stroke="#1B5E20" stroke-width="2">♫</text>
  <text x="1620" y="380" font-size="65" font-weight="bold" fill="#FFD600" stroke="#FF6F00" stroke-width="2">♪</text>
    `;
  }

  // --- THEME 2: OLD MACDONALD'S FARM ---
  _themeFarmAnimals(verseNum) {
    return `
  <!-- Sky -->
  <rect width="1920" height="1080" fill="url(#skyGrad)" />
  <!-- Sun -->
  <circle cx="1680" cy="200" r="90" fill="#FDD835" />
  <circle cx="1680" cy="200" r="130" fill="url(#sunGlow)" />

  <!-- Rolling Farm Pastures -->
  <path d="M -100 650 Q 500 450 1100 620 T 2020 580 L 2020 1080 L -100 1080 Z" fill="url(#hillGrad1)" />
  <path d="M -100 780 Q 700 620 1350 780 T 2020 720 L 2020 1080 L -100 1080 Z" fill="url(#hillGrad2)" />

  <!-- Red Farm Barn -->
  <g transform="translate(250, 420)" filter="url(#softShadow)">
    <polygon points="180,0 20,120 340,120" fill="#D32F2F" stroke="#B71C1C" stroke-width="8" />
    <rect x="20" y="120" width="320" height="260" fill="#E53935" stroke="#B71C1C" stroke-width="8" />
    <!-- Barn Door with X -->
    <rect x="110" y="240" width="140" height="140" fill="#FFFFFF" />
    <line x1="110" y1="240" x2="250" y2="380" stroke="#D32F2F" stroke-width="8" />
    <line x1="250" y1="240" x2="110" y2="380" stroke="#D32F2F" stroke-width="8" />
    <!-- Silo -->
    <rect x="360" y="160" width="90" height="220" rx="15" fill="#CFD8DC" stroke="#78909C" stroke-width="6" />
    <path d="M 360 160 Q 405 90 450 160 Z" fill="#90A4AE" stroke="#78909C" stroke-width="6" />
  </g>

  <!-- Cute Big Hero Cow -->
  <g transform="translate(850, 560)" filter="url(#heroShadow)">
    <!-- Body -->
    <ellipse cx="260" cy="240" rx="180" ry="130" fill="#FFFFFF" stroke="#263238" stroke-width="10" />
    <!-- Black Spots -->
    <path d="M 180 180 Q 220 150 250 190 Q 280 230 220 250 Z" fill="#263238" />
    <path d="M 340 220 Q 380 200 400 240 Q 370 280 330 260 Z" fill="#263238" />
    <!-- Legs -->
    <rect x="140" y="320" width="40" height="110" rx="15" fill="#FFFFFF" stroke="#263238" stroke-width="8" />
    <rect x="140" y="400" width="40" height="30" rx="8" fill="#263238" />
    <rect x="340" y="320" width="40" height="110" rx="15" fill="#FFFFFF" stroke="#263238" stroke-width="8" />
    <rect x="340" y="400" width="40" height="30" rx="8" fill="#263238" />

    <!-- Head -->
    <g transform="translate(40, 80)">
      <circle cx="100" cy="100" r="85" fill="#FFFFFF" stroke="#263238" stroke-width="10" />
      <!-- Horns -->
      <path d="M 60 40 Q 40 10 30 25" stroke="#FFE082" stroke-width="18" stroke-linecap="round" fill="none" />
      <path d="M 140 40 Q 160 10 170 25" stroke="#FFE082" stroke-width="18" stroke-linecap="round" fill="none" />
      <!-- Big Eyes -->
      <ellipse cx="70" cy="90" rx="14" ry="20" fill="#263238" /><circle cx="74" cy="84" r="5" fill="#FFFFFF" />
      <ellipse cx="130" cy="90" rx="14" ry="20" fill="#263238" /><circle cx="134" cy="84" r="5" fill="#FFFFFF" />
      <!-- Cheerful Pink Snout -->
      <ellipse cx="100" cy="135" rx="55" ry="35" fill="#F8BBD0" stroke="#EC407A" stroke-width="6" />
      <circle cx="85" cy="130" r="6" fill="#C2185B" /><circle cx="115" cy="130" r="6" fill="#C2185B" />
      <path d="M 85 145 Q 100 160 115 145" stroke="#C2185B" stroke-width="5" stroke-linecap="round" fill="none" />
      <!-- Cheeks -->
      <circle cx="45" cy="115" r="14" fill="#FF8A80" opacity="0.6" />
      <circle cx="155" cy="115" r="14" fill="#FF8A80" opacity="0.6" />
    </g>
  </g>

  <!-- Playful Chick Beside Cow -->
  <g transform="translate(1420, 780)" filter="url(#softShadow)">
    <circle cx="60" cy="60" r="45" fill="#FFEE58" stroke="#F57F17" stroke-width="6" />
    <polygon points="105,55 125,62 105,70" fill="#FF9800" />
    <circle cx="85" cy="50" r="6" fill="#263238" /><circle cx="87" cy="48" r="2" fill="#FFFFFF" />
    <circle cx="65" cy="68" r="10" fill="#FF8A80" opacity="0.6" />
    <path d="M 45 65 Q 25 70 35 85" stroke="#FDD835" stroke-width="8" stroke-linecap="round" fill="none" />
  </g>
    `;
  }

  // --- THEME 3: BABY DINO STOMP & DANCE ---
  _themeDinosaurJungle(verseNum) {
    return `
  <!-- Sky -->
  <rect width="1920" height="1080" fill="url(#skyGrad)" />
  <!-- Sun & Prehistoric Clouds -->
  <circle cx="300" cy="200" r="100" fill="#FFA726" />
  <circle cx="300" cy="200" r="150" fill="url(#sunGlow)" />

  <!-- Prehistoric Mountains & Jungle Hills -->
  <polygon points="100,600 500,280 850,600" fill="#8D6E63" />
  <polygon points="450,280 500,280 540,320 420,320" fill="#EFEBE9" />
  <polygon points="700,650 1200,320 1650,650" fill="#A1887F" />
  <path d="M -50 720 Q 550 560 1200 740 T 2000 680 L 2000 1080 L -50 1080 Z" fill="#43A047" />
  <path d="M -50 820 Q 800 680 1500 840 T 2000 780 L 2000 1080 L -50 1080 Z" fill="#2E7D32" />

  <!-- Tropical Palm Tree -->
  <g transform="translate(180, 480)">
    <path d="M 50 350 Q 80 180 50 0" stroke="#795548" stroke-width="26" stroke-linecap="round" fill="none" />
    <path d="M 50 0 Q -80 -60 -120 40" stroke="#388E3C" stroke-width="20" stroke-linecap="round" fill="none" />
    <path d="M 50 0 Q 50 -100 80 -40" stroke="#4CAF50" stroke-width="20" stroke-linecap="round" fill="none" />
    <path d="M 50 0 Q 160 -80 200 20" stroke="#388E3C" stroke-width="20" stroke-linecap="round" fill="none" />
  </g>

  <!-- Baby Dinosaur Hero (Cute Green T-Rex) -->
  <g transform="translate(760, 480)" filter="url(#heroShadow)">
    <!-- Big Tail -->
    <path d="M 80 320 Q -80 380 -140 280 Q -100 240 60 260 Z" fill="#66BB6A" stroke="#2E7D32" stroke-width="10" />
    <!-- Body -->
    <ellipse cx="200" cy="300" rx="140" ry="160" fill="#66BB6A" stroke="#2E7D32" stroke-width="10" />
    <!-- Yellow Belly -->
    <ellipse cx="230" cy="320" rx="80" ry="110" fill="#FFF59D" />

    <!-- Big Cute Feet with Sneakers -->
    <ellipse cx="130" cy="450" rx="45" ry="30" fill="#00E5FF" stroke="#0091EA" stroke-width="8" />
    <ellipse cx="270" cy="450" rx="45" ry="30" fill="#00E5FF" stroke="#0091EA" stroke-width="8" />

    <!-- Cute Dino Head -->
    <g transform="translate(140, 60)">
      <path d="M 40 180 Q 20 60 140 40 Q 260 20 280 140 Q 260 220 140 220 Z" fill="#66BB6A" stroke="#2E7D32" stroke-width="10" />
      <!-- Big Expressive Eye -->
      <circle cx="150" cy="110" r="32" fill="#FFFFFF" stroke="#2E7D32" stroke-width="6" />
      <circle cx="160" cy="110" r="18" fill="#1B5E20" />
      <circle cx="166" cy="104" r="7" fill="#FFFFFF" />
      <circle cx="90" cy="155" r="16" fill="#FF8A80" opacity="0.7" />
      <!-- Cheerful Smile & Tiny Dino Teeth -->
      <path d="M 180 160 Q 220 200 260 160" stroke="#1B5E20" stroke-width="8" stroke-linecap="round" fill="none" />
      <polygon points="210,165 218,178 226,165" fill="#FFFFFF" />
      <polygon points="230,165 238,178 246,165" fill="#FFFFFF" />
      <!-- Tiny Arms -->
      <path d="M 60 220 Q 120 250 140 220" stroke="#66BB6A" stroke-width="24" stroke-linecap="round" fill="none" />
    </g>

    <!-- Orange Spikes along Back -->
    <polygon points="120,130 90,90 140,110" fill="#FFA726" stroke="#E65100" stroke-width="5" />
    <polygon points="70,200 30,170 80,185" fill="#FFA726" stroke="#E65100" stroke-width="5" />
    <polygon points="30,270 -10,250 40,265" fill="#FFA726" stroke="#E65100" stroke-width="5" />
  </g>
    `;
  }

  // --- THEME 4: RAINBOW COLORS ---
  _themeRainbowColors(verseNum) {
    return `
  <!-- Sky -->
  <rect width="1920" height="1080" fill="url(#skyGrad)" />
  <!-- Giant Vibrant Rainbow Arc -->
  <g filter="url(#softShadow)">
    <ellipse cx="960" cy="950" rx="850" ry="720" fill="none" stroke="#FF1744" stroke-width="28" />
    <ellipse cx="960" cy="950" rx="822" ry="692" fill="none" stroke="#FF9100" stroke-width="28" />
    <ellipse cx="960" cy="950" rx="794" ry="664" fill="none" stroke="#FFEA00" stroke-width="28" />
    <ellipse cx="960" cy="950" rx="766" ry="636" fill="none" stroke="#00E676" stroke-width="28" />
    <ellipse cx="960" cy="950" rx="738" ry="608" fill="none" stroke="#00B0FF" stroke-width="28" />
    <ellipse cx="960" cy="950" rx="710" ry="580" fill="none" stroke="#D500F9" stroke-width="28" />
  </g>

  <!-- Puffy Clouds Anchoring Rainbow -->
  <g fill="#FFFFFF" filter="url(#softShadow)">
    <circle cx="180" cy="850" r="110" /><circle cx="270" cy="810" r="130" /><circle cx="380" cy="850" r="110" />
    <circle cx="1560" cy="850" r="110" /><circle cx="1670" cy="810" r="130" /><circle cx="1780" cy="850" r="110" />
  </g>

  <!-- Rolling Candy Pastel Hills -->
  <path d="M -50 820 Q 500 700 1100 830 T 2000 760 L 2000 1080 L -50 1080 Z" fill="#F48FB1" />
  <path d="M -50 890 Q 750 780 1450 900 T 2000 850 L 2000 1080 L -50 1080 Z" fill="#CE93D8" />

  <!-- Smiling Paint Palette / Chameleon Character -->
  <g transform="translate(800, 520)" filter="url(#heroShadow)">
    <circle cx="180" cy="180" r="150" fill="#FFF9C4" stroke="#FBC02D" stroke-width="12" />
    <!-- Big Cute Face -->
    <ellipse cx="130" cy="150" rx="16" ry="24" fill="#263238" /><circle cx="136" cy="142" r="6" fill="#FFFFFF" />
    <ellipse cx="230" cy="150" rx="16" ry="24" fill="#263238" /><circle cx="236" cy="142" r="6" fill="#FFFFFF" />
    <circle cx="95" cy="185" r="18" fill="#FF8A80" opacity="0.7" />
    <circle cx="265" cy="185" r="18" fill="#FF8A80" opacity="0.7" />
    <path d="M 140 190 Q 180 230 220 190" stroke="#263238" stroke-width="8" stroke-linecap="round" fill="#FF4081" />

    <!-- Paint Splatters in vibrant rainbow colors -->
    <circle cx="90" cy="90" r="28" fill="#FF1744" />
    <circle cx="180" cy="55" r="28" fill="#FFEA00" />
    <circle cx="270" cy="90" r="28" fill="#00E676" />
    <circle cx="300" cy="180" r="28" fill="#00B0FF" />
  </g>
    `;
  }

  // --- THEME 5: FIVE LITTLE DUCKS ---
  _themeDuckPond(verseNum) {
    return `
  <!-- Sky -->
  <rect width="1920" height="1080" fill="url(#skyGrad)" />
  <circle cx="1650" cy="200" r="85" fill="#FDD835" />

  <!-- Hills Around Pond -->
  <path d="M -50 620 Q 600 480 1200 640 T 2000 580 L 2000 1080 L -50 1080 Z" fill="url(#hillGrad1)" />
  
  <!-- Sparkling Pond -->
  <ellipse cx="960" cy="850" rx="900" ry="280" fill="#29B6F6" stroke="#0288D1" stroke-width="12" />
  <ellipse cx="960" cy="870" rx="820" ry="230" fill="#4FC3F7" />

  <!-- Water Lilies & Reeds -->
  <g fill="#81C784">
    <ellipse cx="350" cy="880" rx="70" ry="25" />
    <ellipse cx="1550" cy="850" rx="80" ry="30" />
  </g>
  <circle cx="350" cy="875" r="15" fill="#FF80AB" />
  <circle cx="1550" cy="845" r="18" fill="#FF80AB" />

  <!-- Mother Duck Hero -->
  <g transform="translate(680, 640)" filter="url(#heroShadow)">
    <ellipse cx="180" cy="160" rx="140" ry="90" fill="#FFEE58" stroke="#F57F17" stroke-width="10" />
    <!-- Wing -->
    <path d="M 120 150 Q 180 200 240 140 Z" fill="#FDD835" stroke="#F57F17" stroke-width="6" />
    <!-- Head -->
    <circle cx="280" cy="100" r="65" fill="#FFEE58" stroke="#F57F17" stroke-width="10" />
    <circle cx="300" cy="85" r="12" fill="#263238" /><circle cx="304" cy="80" r="4" fill="#FFFFFF" />
    <circle cx="260" cy="115" r="14" fill="#FF8A80" opacity="0.6" />
    <!-- Orange Beak -->
    <polygon points="340,90 390,105 340,120" fill="#FF9800" stroke="#E65100" stroke-width="5" />
  </g>

  <!-- Baby Ducklings Following -->
  <g transform="translate(380, 720)" filter="url(#softShadow)">
    <circle cx="80" cy="80" r="45" fill="#FFF59D" stroke="#FBC02D" stroke-width="6" />
    <polygon points="120,75 145,85 120,95" fill="#FFA726" />
    <circle cx="95" cy="70" r="7" fill="#263238" /><circle cx="97" cy="68" r="2" fill="#FFFFFF" />
  </g>
  <g transform="translate(220, 740)" filter="url(#softShadow)">
    <circle cx="70" cy="70" r="38" fill="#FFF59D" stroke="#FBC02D" stroke-width="5" />
    <polygon points="105,65 125,75 105,85" fill="#FFA726" />
    <circle cx="85" cy="62" r="6" fill="#263238" />
  </g>
    `;
  }

  // --- THEME 6: TWINKLE TWINKLE LULLABY ---
  _themeBedtimeLullaby(verseNum) {
    return `
  <!-- Deep Blue Night Sky Gradient -->
  <defs>
    <linearGradient id="nightSky" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#0D1B2A" />
      <stop offset="50%" stop-color="#1B263B" />
      <stop offset="100%" stop-color="#415A77" />
    </linearGradient>
  </defs>
  <rect width="1920" height="1080" fill="url(#nightSky)" />

  <!-- Sparkling Star Field -->
  <g fill="#FFFFFF" opacity="0.85">
    <circle cx="200" cy="180" r="4" /><circle cx="350" cy="120" r="5" /><circle cx="500" cy="240" r="3" />
    <circle cx="800" cy="150" r="5" /><circle cx="1150" cy="100" r="4" /><circle cx="1400" cy="220" r="5" />
    <circle cx="1650" cy="140" r="4" /><circle cx="1800" cy="280" r="5" />
  </g>

  <!-- Smiling Crescent Moon with Nightcap -->
  <g transform="translate(1380, 180)" filter="url(#heroShadow)">
    <path d="M 120 20 A 130 130 0 1 0 230 220 A 100 100 0 1 1 120 20 Z" fill="#FFF59D" stroke="#FBC02D" stroke-width="8" />
    <circle cx="100" cy="110" r="10" fill="#37474F" />
    <circle cx="75" cy="135" r="12" fill="#FF8A80" opacity="0.6" />
    <path d="M 95 135 Q 115 150 105 165" stroke="#37474F" stroke-width="5" stroke-linecap="round" fill="none" />
  </g>

  <!-- Glowing Golden Hero Star -->
  <g transform="translate(820, 360)" filter="url(#heroShadow)">
    <polygon points="140,20 175,95 255,105 195,160 210,240 140,200 70,240 85,160 25,105 105,95" fill="#FFEE58" stroke="#FDD835" stroke-width="12" />
    <!-- Star Face -->
    <ellipse cx="115" cy="130" rx="10" ry="16" fill="#263238" /><circle cx="118" cy="124" r="4" fill="#FFFFFF" />
    <ellipse cx="165" cy="130" rx="10" ry="16" fill="#263238" /><circle cx="168" cy="124" r="4" fill="#FFFFFF" />
    <circle cx="95" cy="145" r="12" fill="#FF8A80" opacity="0.7" />
    <circle cx="185" cy="145" r="12" fill="#FF8A80" opacity="0.7" />
    <path d="M 125 155 Q 140 170 155 155" stroke="#263238" stroke-width="6" stroke-linecap="round" fill="none" />
  </g>

  <!-- Soft Dreamy Night Clouds -->
  <g fill="#5C6BC0" opacity="0.5">
    <ellipse cx="500" cy="980" rx="600" ry="180" />
    <ellipse cx="1400" cy="960" rx="650" ry="200" />
  </g>
    `;
  }

  // --- THEME 7: ALPHABET SAFARI ---
  _themeAlphabetSafari(verseNum) {
    return `
  <!-- Sky -->
  <rect width="1920" height="1080" fill="url(#skyGrad)" />
  <circle cx="240" cy="200" r="90" fill="#FDD835" />

  <!-- Safari Savannah Hills -->
  <path d="M -50 680 Q 550 520 1150 690 T 2000 640 L 2000 1080 L -50 1080 Z" fill="#DCE775" />
  <path d="M -50 800 Q 800 660 1450 820 T 2000 760 L 2000 1080 L -50 1080 Z" fill="#C0CA33" />

  <!-- Acacia Tree -->
  <path d="M 1550 850 Q 1580 620 1620 480" stroke="#5D4037" stroke-width="26" stroke-linecap="round" fill="none" />
  <ellipse cx="1620" cy="460" rx="180" ry="60" fill="#388E3C" />
  <ellipse cx="1520" cy="440" rx="140" ry="50" fill="#2E7D32" />

  <!-- ABC Wooden Blocks -->
  <g transform="translate(420, 680)" filter="url(#softShadow)">
    <rect x="0" y="80" width="130" height="130" rx="20" fill="#E53935" stroke="#B71C1C" stroke-width="8" />
    <text x="65" y="175" font-size="95" font-weight="900" font-family="Arial, sans-serif" fill="#FFFFFF" text-anchor="middle">A</text>

    <rect x="145" y="80" width="130" height="130" rx="20" fill="#1E88E5" stroke="#0D47A1" stroke-width="8" />
    <text x="210" y="175" font-size="95" font-weight="900" font-family="Arial, sans-serif" fill="#FFFFFF" text-anchor="middle">B</text>

    <rect x="75" y="-55" width="130" height="130" rx="20" fill="#FDD835" stroke="#F57F17" stroke-width="8" />
    <text x="140" y="40" font-size="95" font-weight="900" font-family="Arial, sans-serif" fill="#FFFFFF" text-anchor="middle">C</text>
  </g>

  <!-- Friendly Safari Lion Cub -->
  <g transform="translate(940, 560)" filter="url(#heroShadow)">
    <!-- Mane -->
    <circle cx="200" cy="180" r="140" fill="#FB8C00" stroke="#E65100" stroke-width="10" />
    <!-- Face -->
    <circle cx="200" cy="180" r="95" fill="#FFE082" stroke="#FFA000" stroke-width="8" />
    <!-- Ears -->
    <circle cx="120" cy="95" r="30" fill="#FB8C00" /><circle cx="120" cy="95" r="16" fill="#FFE082" />
    <circle cx="280" cy="95" r="30" fill="#FB8C00" /><circle cx="280" cy="95" r="16" fill="#FFE082" />
    <!-- Big Eyes -->
    <ellipse cx="165" cy="165" rx="14" ry="20" fill="#263238" /><circle cx="169" cy="159" r="5" fill="#FFFFFF" />
    <ellipse cx="235" cy="165" rx="14" ry="20" fill="#263238" /><circle cx="239" cy="159" r="5" fill="#FFFFFF" />
    <!-- Nose & Smile -->
    <polygon points="190,195 210,195 200,210" fill="#D84315" />
    <path d="M 185 215 Q 200 230 215 215" stroke="#263238" stroke-width="6" stroke-linecap="round" fill="none" />
    <circle cx="140" cy="190" r="14" fill="#FF8A80" opacity="0.6" />
    <circle cx="260" cy="190" r="14" fill="#FF8A80" opacity="0.6" />
  </g>
    `;
  }

  // --- THEME 8: PLAYGROUND / CELEBRATION FALLBACK ---
  _themePlaygroundCelebration(verseNum) {
    return `
  <!-- Sky -->
  <rect width="1920" height="1080" fill="url(#skyGrad)" />
  <circle cx="220" cy="200" r="90" fill="#FDD835" />

  <!-- Confetti / Balloons in background -->
  <circle cx="450" cy="260" r="28" fill="#FF4081" /><path d="M 450 288 Q 440 340 460 380" stroke="#757575" stroke-width="3" fill="none" />
  <circle cx="1520" cy="220" r="32" fill="#00E676" /><path d="M 1520 252 Q 1530 300 1510 350" stroke="#757575" stroke-width="3" fill="none" />
  <circle cx="1650" cy="300" r="28" fill="#FFD600" /><path d="M 1650 328 Q 1660 380 1640 420" stroke="#757575" stroke-width="3" fill="none" />

  <!-- Cheerful Rolling Hills -->
  <path d="M -50 680 Q 550 520 1150 690 T 2000 640 L 2000 1080 L -50 1080 Z" fill="url(#hillGrad1)" />
  <path d="M -50 800 Q 800 660 1450 820 T 2000 760 L 2000 1080 L -50 1080 Z" fill="url(#hillGrad2)" />

  <!-- Joyful Dancing Character Hero -->
  <g transform="translate(820, 520)" filter="url(#heroShadow)">
    <!-- Dancing Bear -->
    <ellipse cx="140" cy="260" rx="100" ry="120" fill="#8D6E63" stroke="#5D4037" stroke-width="10" />
    <ellipse cx="140" cy="270" rx="60" ry="75" fill="#D7CCC8" />
    <!-- Arms in Celebration Wave -->
    <path d="M 60 210 Q -20 140 20 100" stroke="#8D6E63" stroke-width="32" stroke-linecap="round" fill="none" />
    <path d="M 220 210 Q 300 140 260 100" stroke="#8D6E63" stroke-width="32" stroke-linecap="round" fill="none" />
    <!-- Head -->
    <circle cx="140" cy="110" r="75" fill="#8D6E63" stroke="#5D4037" stroke-width="10" />
    <!-- Ears with Pink Center -->
    <circle cx="75" cy="45" r="28" fill="#8D6E63" /><circle cx="75" cy="45" r="15" fill="#FFAB91" />
    <circle cx="205" cy="45" r="28" fill="#8D6E63" /><circle cx="205" cy="45" r="15" fill="#FFAB91" />
    <!-- Eyes -->
    <ellipse cx="115" cy="100" rx="11" ry="16" fill="#263238" /><circle cx="118" cy="95" r="4" fill="#FFFFFF" />
    <ellipse cx="165" cy="100" rx="11" ry="16" fill="#263238" /><circle cx="168" cy="95" r="4" fill="#FFFFFF" />
    <!-- Snout & Smile -->
    <ellipse cx="140" cy="130" rx="30" ry="20" fill="#D7CCC8" />
    <ellipse cx="140" cy="122" rx="10" ry="7" fill="#3E2723" />
    <path d="M 130 135 Q 140 146 150 135" stroke="#3E2723" stroke-width="5" stroke-linecap="round" fill="none" />
    <circle cx="95" cy="125" r="14" fill="#FF8A80" opacity="0.6" />
    <circle cx="185" cy="125" r="14" fill="#FF8A80" opacity="0.6" />
  </g>
    `;
  }

  /**
   * OpenAI DALL-E 3 image generation fallback
   */
  async _generateWithDalle(promptText) {
    const prompt = `Pixar Disney Junior style 3D cartoon, vibrant saturated colors, cheerful smiling character: ${promptText}, warm soft lighting, 8k resolution, child friendly`;
    const res = await axios.post('https://api.openai.com/v1/images/generations', {
      model: 'dall-e-3',
      prompt: prompt,
      n: 1,
      size: '1792x1024'
    }, {
      headers: {
        'Authorization': `Bearer ${config.ai.openaiApiKey}`,
        'Content-Type': 'application/json'
      }
    });
    return res.data?.data?.[0]?.url;
  }
}

module.exports = new SceneGenerator();
