const sharp = require('sharp');
const fs = require('fs');
const path = require('path');
const config = require('../../config');

/**
 * Character Design & Profile Creator
 * Generates persistent cartoon characters, character sheets, and visual model cards
 * designed for cross-scene visual consistency in Google Veo 2 / Google Flow videos.
 */
class CharacterCreator {
  constructor() {
    this.characters = [
      {
        id: 'barnaby-bunny',
        name: 'Barnaby the Bunny',
        species: 'Baby Bunny',
        archetype: 'The Joyful Explorer',
        colors: {
          primary: '#4FC3F7',
          secondary: '#FFE600',
          accent: '#FF1744',
          belly: '#FFFFFF',
          blush: '#FF8A80'
        },
        appearance: 'chubby fluffy sky-blue baby bunny, enormous expressive anime eyes with white sparkle highlights, long floppy ears with pastel pink insides, happy rosy cheeks, cute round white cotton tail',
        outfit: 'bright yellow toddler dungarees with big red circular buttons and a cute red satin bowtie',
        personality: 'curious, bouncy, joyful, always hopping, clapping, and singing with toddler enthusiasm',
        bestForThemes: ['vehicles', 'bus', 'wheels', 'colors', 'general', 'playground', 'dance']
      },
      {
        id: 'pip-duckling',
        name: 'Pip the Duckling',
        species: 'Baby Duckling',
        archetype: 'The Cheerful Swimmer',
        colors: {
          primary: '#FFD600',
          secondary: '#FF6D00',
          accent: '#00E5FF',
          belly: '#FFF9C4',
          blush: '#FFAB91'
        },
        appearance: 'fluffy golden-yellow baby duckling, big glossy cute cartoon eyes, round chubby body, bright orange beak and little webbed feet, tiny yellow wings flapping happily',
        outfit: 'tiny cyan polka-dot sailor hat perched tilted between ears',
        personality: 'playful, splashing cheerfully in water, waddling happily, quacking to the rhythm',
        bestForThemes: ['duck', 'pond', 'water', 'counting', 'bath', 'swimming', 'lake']
      },
      {
        id: 'rexy-dino',
        name: 'Rexy the Baby Dinosaur',
        species: 'Baby T-Rex',
        archetype: 'The Energetic Stomper',
        colors: {
          primary: '#76FF03',
          secondary: '#FF5722',
          accent: '#FFEB3B',
          belly: '#FFF59D',
          blush: '#FF8A80'
        },
        appearance: 'cute friendly baby lime-green T-Rex, soft rounded snout with tiny harmless white cartoon teeth, big round emerald cartoon eyes, pastel yellow belly, soft orange dorsal spikes along back',
        outfit: 'tiny bright red toddler sneakers with white laces on his chunky feet',
        personality: 'energetic, stomping happily, doing adorable playful baby roars, laughing and bopping',
        bestForThemes: ['dino', 'dinosaur', 'stomp', 'jungle', 'prehistoric', 'active', 'roar']
      },
      {
        id: 'leo-lion',
        name: 'Leo the Lion Cub',
        species: 'Baby Lion Cub',
        archetype: 'The Brave Friend',
        colors: {
          primary: '#FFB300',
          secondary: '#8D6E63',
          accent: '#29B6F6',
          belly: '#FFF8E1',
          blush: '#FF8A80'
        },
        appearance: 'adorable golden-amber baby lion cub, fluffy cinnamon mane, big warm amber cartoon eyes, cheerful white muzzle and soft pink nose, fuzzy round ears',
        outfit: 'little royal-blue safari bandana tied neatly around neck',
        personality: 'brave, cheerful, clapping paws, exploring sunny grasslands, purring cheerfully',
        bestForThemes: ['lion', 'safari', 'animals', 'farm', 'zoo', 'adventure', 'jungle']
      },
      {
        id: 'dotti-elephant',
        name: 'Dotti the Baby Elephant',
        species: 'Baby Elephant',
        archetype: 'The Musical Dreamer',
        colors: {
          primary: '#BA68C8',
          secondary: '#F48FB1',
          accent: '#FFEB3B',
          belly: '#F3E5F5',
          blush: '#FF4081'
        },
        appearance: 'tiny sweet baby lilac-purple elephant, giant soft fan-shaped ears that flutter rhythmically, big sparkling lavender eyes, curling little trunk happily upward',
        outfit: 'vibrant yellow daisy flower crown sitting atop head',
        personality: 'gentle, musical, blowing joyful water bubbles, swaying peacefully, loving lullabies',
        bestForThemes: ['lullaby', 'bedtime', 'star', 'sleep', 'gentle', 'night', 'clouds']
      }
    ];
  }

  /**
   * Selects or designs the most appropriate character for a song
   * @param {Object} song
   */
  getCharacterForSong(song) {
    const text = `${song.theme || ''} ${song.id || ''} ${song.title || ''}`.toLowerCase();

    if (text.includes('dino') || text.includes('roar') || text.includes('prehistoric')) {
      return this.characters.find(c => c.id === 'rexy-dino') || this.characters[2];
    }
    if (text.includes('duck') || text.includes('pond') || text.includes('quack') || text.includes('splash') || text.includes('swim')) {
      return this.characters.find(c => c.id === 'pip-duckling') || this.characters[1];
    }
    if (text.includes('lion') || text.includes('safari') || text.includes('farm') || text.includes('zoo')) {
      return this.characters.find(c => c.id === 'leo-lion') || this.characters[3];
    }
    if (text.includes('lullaby') || text.includes('bedtime') || text.includes('star') || text.includes('sleep') || text.includes('night')) {
      return this.characters.find(c => c.id === 'dotti-elephant') || this.characters[4];
    }

    // Default: Barnaby the Bunny (vehicles, colors, numbers, counting, cheerful dance)
    return this.characters[0];
  }

  /**
   * Returns consistent character prompt tokens for Google Veo 2 / AI Video generation
   * @param {Object} character
   */
  getCharacterPromptTokens(character) {
    return `Character: ${character.name}, a 3D Pixar-style ${character.appearance}, wearing ${character.outfit}. Expressive 3D Disney Junior render, vibrant cute face, big cartoon anime eyes with highlight sparkles. Personality: ${character.personality}. Colors: ${character.colors.primary} and ${character.colors.secondary}.`;
  }

  /**
   * Generates a high-res 1920x1080 visual Character Model Card for the song project
   * @param {Object} character
   * @param {string} outputPath
   */
  async generateCharacterCard(character, outputPath) {
    const dir = path.dirname(outputPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    const c = character;
    const escapeXml = (str) => String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    const safeName = escapeXml(c.name);
    const safeSpecies = escapeXml(c.species);
    const safeArchetype = escapeXml(c.archetype);
    const safeAppearance = escapeXml(c.appearance);
    const safeOutfit = escapeXml(c.outfit);
    const safePersonality = escapeXml(c.personality);

    const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F0C29" />
      <stop offset="50%" stop-color="#302B63" />
      <stop offset="100%" stop-color="#24243E" />
    </linearGradient>

    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="${c.colors.primary}" flood-opacity="0.6" />
    </filter>
    <filter id="cardShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="16" stdDeviation="20" flood-color="#000000" flood-opacity="0.7" />
    </filter>
  </defs>

  <!-- Background -->
  <rect width="1920" height="1080" fill="url(#bgGrad)" />

  <!-- Decorative Background Circles -->
  <circle cx="200" cy="180" r="320" fill="${c.colors.primary}" opacity="0.12" />
  <circle cx="1700" cy="850" r="400" fill="${c.colors.secondary}" opacity="0.10" />

  <!-- Left Main Character Stage Card -->
  <g filter="url(#cardShadow)">
    <rect x="100" y="80" width="800" height="920" rx="40" fill="#1C1844" stroke="${c.colors.primary}" stroke-width="6" />
  </g>

  <!-- Character 3D Illustration Stand -->
  <ellipse cx="500" cy="780" rx="260" ry="40" fill="#000000" opacity="0.4" />
  <ellipse cx="500" cy="775" rx="240" ry="32" fill="${c.colors.primary}" opacity="0.3" filter="url(#glow)" />

  <!-- Stylized Character Avatar -->
  <!-- Body -->
  <ellipse cx="500" cy="560" rx="170" ry="190" fill="${c.colors.primary}" stroke="#FFFFFF" stroke-width="4" filter="url(#glow)" />
  <ellipse cx="500" cy="590" rx="110" ry="120" fill="${c.colors.belly}" />

  <!-- Head -->
  <circle cx="500" cy="360" r="160" fill="${c.colors.primary}" stroke="#FFFFFF" stroke-width="4" />

  <!-- Cheeks -->
  <circle cx="410" cy="390" r="32" fill="${c.colors.blush}" opacity="0.8" />
  <circle cx="590" cy="390" r="32" fill="${c.colors.blush}" opacity="0.8" />

  <!-- Big Anime Eyes -->
  <ellipse cx="435" cy="330" rx="35" ry="45" fill="#1A1A2E" />
  <ellipse cx="565" cy="330" rx="35" ry="45" fill="#1A1A2E" />
  <circle cx="445" cy="318" r="14" fill="#FFFFFF" />
  <circle cx="426" cy="342" r="7" fill="#FFFFFF" />
  <circle cx="575" cy="318" r="14" fill="#FFFFFF" />
  <circle cx="556" cy="342" r="7" fill="#FFFFFF" />

  <!-- Smile -->
  <path d="M 460 385 Q 500 425 540 385" stroke="#D81B60" stroke-width="9" stroke-linecap="round" fill="none" />
  <path d="M 470 388 Q 500 422 530 388" fill="#FF5252" />

  <!-- Character Nameplate Badge -->
  <rect x="220" y="820" width="560" height="90" rx="45" fill="${c.colors.secondary}" stroke="#FFFFFF" stroke-width="4" filter="url(#glow)" />
  <text x="500" y="878" font-family="'Arial Rounded MT Bold', sans-serif" font-size="38" font-weight="900" fill="#1A0A38" text-anchor="middle">${safeName.toUpperCase()}</text>

  <!-- Right Information & Model Specifications Card -->
  <g filter="url(#cardShadow)">
    <rect x="950" y="80" width="870" height="920" rx="40" fill="#18153A" stroke="#4A3F82" stroke-width="3" />
  </g>

  <!-- Header -->
  <text x="1000" y="160" font-family="'Arial Rounded MT Bold', sans-serif" font-size="28" font-weight="900" fill="#00E5FF" letter-spacing="3">OFFICIAL CHARACTER SPECIFICATION SHEET</text>
  <text x="1000" y="225" font-family="'Arial Rounded MT Bold', sans-serif" font-size="52" font-weight="900" fill="#FFFFFF">${safeName}</text>
  <text x="1000" y="270" font-family="'Arial Rounded MT Bold', sans-serif" font-size="26" font-weight="700" fill="#FFE600">Archetype: ${safeArchetype} (${safeSpecies})</text>

  <!-- Divider -->
  <line x1="1000" y1="300" x2="1750" y2="300" stroke="#4A3F82" stroke-width="2" />

  <!-- Appearance Section -->
  <text x="1000" y="355" font-family="'Arial Rounded MT Bold', sans-serif" font-size="22" font-weight="900" fill="#FF80AB">VISUAL DESIGN &amp; PROPORTIONS:</text>
  <text x="1000" y="390" font-family="Arial, sans-serif" font-size="18" fill="#E0E0E0">${safeAppearance.slice(0, 65)}</text>
  <text x="1000" y="420" font-family="Arial, sans-serif" font-size="18" fill="#E0E0E0">${safeAppearance.slice(65, 130)}</text>
  <text x="1000" y="450" font-family="Arial, sans-serif" font-size="18" fill="#E0E0E0">${safeAppearance.slice(130, 200)}</text>

  <!-- Outfit Section -->
  <text x="1000" y="520" font-family="'Arial Rounded MT Bold', sans-serif" font-size="22" font-weight="900" fill="#FFD54F">SIGNATURE OUTFIT:</text>
  <text x="1000" y="555" font-family="Arial, sans-serif" font-size="18" fill="#E0E0E0">${safeOutfit.slice(0, 65)}</text>
  <text x="1000" y="585" font-family="Arial, sans-serif" font-size="18" fill="#E0E0E0">${safeOutfit.slice(65, 130)}</text>

  <!-- Personality Section -->
  <text x="1000" y="650" font-family="'Arial Rounded MT Bold', sans-serif" font-size="22" font-weight="900" fill="#80D8FF">ANIMATION PERSONALITY &amp; MOTION BEHAVIOR:</text>
  <text x="1000" y="685" font-family="Arial, sans-serif" font-size="18" fill="#E0E0E0">${safePersonality.slice(0, 65)}</text>
  <text x="1000" y="715" font-family="Arial, sans-serif" font-size="18" fill="#E0E0E0">${safePersonality.slice(65, 130)}</text>

  <!-- Palette Swatches -->
  <text x="1000" y="775" font-family="'Arial Rounded MT Bold', sans-serif" font-size="22" font-weight="900" fill="#B388FF">CONSISTENT BRAND COLOR PALETTE:</text>
  <circle cx="1030" cy="820" r="26" fill="${c.colors.primary}" stroke="#FFFFFF" stroke-width="3" />
  <circle cx="1100" cy="820" r="26" fill="${c.colors.secondary}" stroke="#FFFFFF" stroke-width="3" />
  <circle cx="1170" cy="820" r="26" fill="${c.colors.accent}" stroke="#FFFFFF" stroke-width="3" />
  <circle cx="1240" cy="820" r="26" fill="${c.colors.belly}" stroke="#FFFFFF" stroke-width="3" />
  <circle cx="1310" cy="820" r="26" fill="${c.colors.blush}" stroke="#FFFFFF" stroke-width="3" />

  <!-- Google Flow / Veo Engine Consistency Badge -->
  <rect x="1000" y="875" width="770" height="80" rx="20" fill="#13233F" stroke="#00E5FF" stroke-width="2" />
  <text x="1030" y="915" font-family="'Arial Rounded MT Bold', sans-serif" font-size="20" font-weight="900" fill="#00E5FF">⚡ GOOGLE FLOW / VEO 2 CONSISTENCY LOCK</text>
  <text x="1030" y="940" font-family="Arial, sans-serif" font-size="14" fill="#B0BEC5">Prompts pass strict character tokens across all scenes for persistent 3D animation.</text>
</svg>
    `;

    await sharp(Buffer.from(svg))
      .resize(1920, 1080)
      .png()
      .toFile(outputPath);

    return outputPath;
  }
}

module.exports = new CharacterCreator();
