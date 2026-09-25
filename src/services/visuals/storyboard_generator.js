const config = require('../../config');
const characterCreator = require('./character_creator');
const fs = require('fs');
const path = require('path');

/**
 * Storyboard Generator
 * Generates scene-by-scene motion storyboards formatted for Google Veo 2 / Google Flow video generation.
 * Ensures consistent characters, cinematic camera motions, and rhythmic preschool actions.
 */
class StoryboardGenerator {
  constructor() {
    this.characterCreator = characterCreator;
  }

  /**
   * Generates a multi-scene storyboard for a song with persistent character design
   * @param {Object} song Song object containing verses, title, theme
   */
  async generateStoryboard(song) {
    const character = this.characterCreator.getCharacterForSong(song);
    const verses = song.verses || [];

    // Cinematic shot variety for engaging toddler visual rhythm
    const shotArchetypes = [
      {
        name: 'Opening Establishing Wide',
        camera: 'cinematic wide establishing shot with smooth forward dolly',
        lighting: 'warm golden morning sunlight, soft volumetric godrays, pastel skies',
        motionPrompt: 'smooth 3D camera tracks slowly forward through a colorful wonderland'
      },
      {
        name: 'Dynamic Medium Dance',
        camera: 'medium action shot with playful rhythm bounce and side-tracking',
        lighting: 'vibrant saturated daylight, sparkle particle accents floating around',
        motionPrompt: 'dynamic camera sways with the 124 BPM music rhythm while keeping character centered'
      },
      {
        name: 'Expressive Singing Close-Up',
        camera: 'intimate close-up with gentle orbital camera movement',
        lighting: 'bright glowing highlights on character eyes, warm peach fill light',
        motionPrompt: 'camera gently orbits 15 degrees around the character smiling and singing happily'
      },
      {
        name: 'Celebratory Finale Wide',
        camera: 'wide celebratory crane-up shot with cheerful confetti and sparkles',
        lighting: 'magical twilight rainbow glow, glowing stars and confetti',
        motionPrompt: 'camera smoothly cranes upward revealing the full vibrant cartoon world in celebration'
      }
    ];

    const scenes = [];

    for (let i = 0; i < verses.length; i++) {
      const v = verses[i];
      const shot = shotArchetypes[i % shotArchetypes.length];
      const sceneNum = i + 1;
      const action = this._getVerseAction(v.lyrics, character.name);

      // Google Flow / Google Veo 2 Prompt
      const veoPrompt = `Pixar 3D animated film aesthetic, Disney Junior animation style. 
Character: ${character.name}, ${character.appearance}, wearing ${character.outfit}. 
Action: ${action}. High energy, cheerful preschool appeal, bouncing rhythmically to the music. 
Setting: Vibrant 3D cartoon world, ${v.sceneDescription || 'lush rolling green hills, rainbow sky, sunny fluffy cartoon clouds'}. 
Cinematography: ${shot.camera}, ${shot.motionPrompt}, ${shot.lighting}, 60fps smooth 3D motion, rich saturated colors, cinematic depth of field, 4k render, no text, child friendly.`.replace(/\s+/g, ' ').trim();

      scenes.push({
        sceneNumber: sceneNum,
        verseNumber: v.verseNumber || sceneNum,
        lyrics: v.lyrics,
        character: {
          id: character.id,
          name: character.name,
          species: character.species,
          colors: character.colors
        },
        shotName: shot.name,
        cameraShot: shot.camera,
        lighting: shot.lighting,
        action: action,
        durationSec: v.durationSec || 6.5,
        veoPrompt: veoPrompt
      });
    }

    const storyboard = {
      songTitle: song.title,
      songTheme: song.theme,
      character: character,
      totalScenes: scenes.length,
      scenes: scenes,
      generatedAt: new Date().toISOString()
    };

    return storyboard;
  }

  /**
   * Saves storyboard data and an HTML visual presentation for review
   * @param {Object} storyboard
   * @param {string} outputDir
   */
  async saveStoryboard(storyboard, outputDir) {
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

    // 1. Save JSON
    const jsonPath = path.join(outputDir, 'storyboard.json');
    fs.writeFileSync(jsonPath, JSON.stringify(storyboard, null, 2));

    // 2. Save HTML Visual Presentation
    const htmlPath = path.join(outputDir, 'storyboard.html');
    const html = this._generateHtmlStoryboard(storyboard);
    fs.writeFileSync(htmlPath, html);

    return { jsonPath, htmlPath };
  }

  _generateHtmlStoryboard(sb) {
    const c = sb.character;
    const sceneCards = sb.scenes.map(s => `
      <div class="scene-card">
        <div class="scene-header">
          <span class="scene-badge">SCENE ${s.sceneNumber}</span>
          <span class="shot-badge">${s.shotName}</span>
        </div>
        <div class="lyrics-quote">"${s.lyrics}"</div>
        <div class="detail-row"><strong>Action:</strong> ${s.action}</div>
        <div class="detail-row"><strong>Camera:</strong> ${s.cameraShot}</div>
        <div class="detail-row"><strong>Lighting:</strong> ${s.lighting}</div>
        <div class="veo-prompt-box">
          <div class="veo-label">⚡ GOOGLE FLOW / VEO 2 PROMPT:</div>
          <code>${s.veoPrompt}</code>
        </div>
      </div>
    `).join('\n');

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Storyboard: ${sb.songTitle}</title>
  <style>
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0E0B1F; color: #FFF; margin: 0; padding: 30px; }
    .header { text-align: center; margin-bottom: 40px; }
    h1 { font-size: 36px; color: #FFE600; margin-bottom: 5px; }
    .meta { font-size: 18px; color: #80D8FF; }
    .char-banner { background: #1C1738; border-radius: 16px; padding: 25px; margin-bottom: 40px; border-left: 8px solid ${c.colors.primary}; }
    .scenes-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 24px; }
    .scene-card { background: #181432; border-radius: 16px; padding: 24px; border: 1px solid #332B5C; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
    .scene-header { display: flex; justify-content: space-between; margin-bottom: 12px; }
    .scene-badge { background: #FF4081; color: #FFF; font-weight: 900; padding: 4px 12px; border-radius: 20px; font-size: 12px; }
    .shot-badge { background: #00E5FF; color: #000; font-weight: 800; padding: 4px 12px; border-radius: 20px; font-size: 12px; }
    .lyrics-quote { font-size: 19px; font-weight: bold; color: #FFF176; margin-bottom: 14px; font-style: italic; }
    .detail-row { font-size: 14px; color: #CFD8DC; margin-bottom: 8px; line-height: 1.4; }
    .veo-prompt-box { background: #0C091A; border-radius: 10px; padding: 14px; margin-top: 14px; border: 1px solid #00E5FF; }
    .veo-label { font-size: 11px; font-weight: 900; color: #00E5FF; margin-bottom: 6px; letter-spacing: 1px; }
    code { font-size: 12px; color: #B388FF; line-height: 1.4; word-break: break-word; display: block; }
  </style>
</head>
<body>
  <div class="header">
    <h1>🎬 3D CARTOON MOTION STORYBOARD</h1>
    <div class="meta">${sb.songTitle} • Character: ${c.name} • ${sb.totalScenes} Sequential Scenes</div>
  </div>
  <div class="char-banner">
    <h2>⭐ Character: ${c.name} (${c.archetype})</h2>
    <p><strong>Appearance:</strong> ${c.appearance}</p>
    <p><strong>Signature Outfit:</strong> ${c.outfit}</p>
    <p><strong>Animation Behavior:</strong> ${c.personality}</p>
  </div>
  <div class="scenes-grid">
    ${sceneCards}
  </div>
</body>
</html>`;
  }

  _getVerseAction(lyrics, characterName) {
    const lower = (lyrics || '').toLowerCase();
    if (lower.includes('round and round') || lower.includes('bus') || lower.includes('wheel')) {
      return `${characterName} is happily driving a bright yellow cartoon bus, waving merrily out the window and bobbing up and down to the catchy toddler beat`;
    }
    if (lower.includes('stomp') || lower.includes('roar') || lower.includes('dino')) {
      return `${characterName} is playfully stomping two feet in rhythm with the music, doing a sweet cute little roar with arms raised in pure joy`;
    }
    if (lower.includes('clap') || lower.includes('happy') || lower.includes('hand')) {
      return `${characterName} is clapping two hands rhythmically together, with colorful musical sparkle bursts floating all around and an enormous joyful smile`;
    }
    if (lower.includes('quack') || lower.includes('duck') || lower.includes('water') || lower.includes('swim')) {
      return `${characterName} is playfully paddling across sparkling turquoise water, splashing water droplets in rhythm and laughing happily`;
    }
    if (lower.includes('twinkle') || lower.includes('star') || lower.includes('sleep') || lower.includes('moon')) {
      return `${characterName} is gently swaying beneath a smiling golden crescent moon, watching friendly golden stars dance and twinkle in the night sky`;
    }
    if (lower.includes('rainbow') || lower.includes('color') || lower.includes('red') || lower.includes('blue')) {
      return `${characterName} is dancing along a glowing pastel rainbow bridge, tossing shimmering colorful glitter petals into the air with delight`;
    }
    return `${characterName} is dancing cheerfully, hopping rhythmically from foot to foot and swinging arms to the catchy rhythm with a big bright smile`;
  }
}

module.exports = new StoryboardGenerator();
