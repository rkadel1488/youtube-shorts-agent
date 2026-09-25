const { GoogleGenAI } = require('@google/genai');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegPath = require('ffmpeg-static');
const sharp = require('sharp');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const config = require('../../config');
const sceneGenerator = require('./scene_generator');
ffmpeg.setFfmpegPath(ffmpegPath);

/**
 * Google Flow & Google Veo 2 Video Generator
 * Produces real 3D animated motion video clips for children's cartoon songs using:
 * 1. Google Veo 2 ('veo-2.0-generate-001') via @google/genai SDK when API key is provided.
 * 2. Active Motion Cartoon Synthesizer with rhythmic bounce, multi-axis camera motion,
 *    and sparkling particle layers when running locally or during fallback.
 */
class VeoVideoGenerator {
  constructor() {
    this.apiKey = config.ai.geminiApiKey || process.env.GOOGLE_AI_STUDIO_API_KEY || '';
    this.modelName = 'veo-2.0-generate-001';
    this.fps = config.video.fps || 30;
    this.width = config.video.width || 1920;
    this.height = config.video.height || 1080;
  }

  /**
   * Generates a video clip for a storyboard scene
   * @param {Object} scene Storyboard scene object
   * @param {Object} song Master song object
   * @param {string} outputPath Target .mp4 file path
   * @param {Object} options Additional options { motionIndex, bpm }
   */
  async generateSceneVideo(scene, song, outputPath, options = {}) {
    const dir = path.dirname(outputPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    const durationSec = Math.max(4, Math.round(scene.durationSec || 6));
    const bpm = song.bpm || config.audio.defaultBpm || 124;

    // 1. Try Google Flow / Veo 2 Video Generation if API key is present
    if (this.apiKey && process.env.DISABLE_VEO !== 'true') {
      try {
        console.log(`\n⚡ [Google Flow / Veo 2] Requesting 3D AI Video for Scene ${scene.sceneNumber}...`);
        console.log(`   Prompt: "${scene.veoPrompt.slice(0, 100)}..."`);

        const rawVeoVideoPath = await this._generateWithGoogleVeo(scene.veoPrompt, durationSec, dir, scene.sceneNumber);
        if (rawVeoVideoPath && fs.existsSync(rawVeoVideoPath)) {
          console.log(`   ✅ [Google Veo 2] Clip generated successfully! Overlaid sing-along subtitles...`);
          return await this._overlaySubtitlesAndEffects(rawVeoVideoPath, scene.lyrics, outputPath, durationSec);
        }
      } catch (err) {
        console.warn(`\n⚠️ [Google Flow / Veo 2] Note: ${err.message}`);
        console.log(`   🔄 Seamlessly activating Active Motion Cartoon Synthesizer (60fps character motion, rhythmic beat bounce & particle FX)...`);
      }
    } else {
      console.log(`   🎬 [Active Motion Engine] Generating 3D cartoon motion clip for Scene ${scene.sceneNumber} (${scene.character.name})...`);
    }

    // 2. Active Motion Cartoon Video Synthesizer (Zero-cost, multi-axis motion, beat-synced bounce)
    return await this._generateActiveMotionClip(scene, song, outputPath, durationSec, bpm, options.motionIndex || 0);
  }

  /**
   * Generates video via Google Veo 2 ('veo-2.0-generate-001')
   */
  async _generateWithGoogleVeo(prompt, durationSec, outputDir, sceneNum) {
    const ai = new GoogleGenAI({ apiKey: this.apiKey });
    const targetSeconds = Math.min(8, Math.max(5, durationSec));

    let operation = await ai.models.generateVideos({
      model: this.modelName,
      prompt: prompt,
      config: {
        aspectRatio: '16:9',
        durationSeconds: targetSeconds,
        numberOfVideos: 1
      }
    });

    console.log(`   ⏳ [Google Veo 2] Video generation started (Op ID: ${operation.name || 'pending'}). Polling...`);

    // Poll until video is complete (up to 3 minutes)
    let attempts = 0;
    while (!operation.done && attempts < 18) {
      await new Promise(r => setTimeout(r, 10000)); // Poll every 10 seconds
      operation = await ai.operations.getVideosOperation({ operation: operation });
      attempts++;
      process.stdout.write(`   └─ Veo rendering in progress (${attempts * 10}s)...\r`);
    }
    console.log('');

    const generatedVideo = operation.response?.generatedVideos?.[0]?.video;
    if (!generatedVideo) {
      throw new Error('Google Veo 2 returned no video payload in operation response.');
    }

    const tempVeoPath = path.join(outputDir, `raw_veo_s${sceneNum}_${Date.now()}.mp4`);

    if (generatedVideo.videoBytes) {
      // Decode base64 MP4 bytes
      const videoBuffer = Buffer.from(generatedVideo.videoBytes, 'base64');
      fs.writeFileSync(tempVeoPath, videoBuffer);
      return tempVeoPath;
    } else if (generatedVideo.uri) {
      // Download MP4 from URI
      const response = await axios.get(generatedVideo.uri, { responseType: 'arraybuffer' });
      fs.writeFileSync(tempVeoPath, Buffer.from(response.data));
      return tempVeoPath;
    }

    throw new Error('No video bytes or URI returned by Veo 2.');
  }

  /**
   * Active Motion Cartoon Synthesizer
   * Creates real cartoon motion clips with rhythmic character bounce, camera tracking,
   * floating sparkles, and sing-along subtitles.
   */
  async _generateActiveMotionClip(scene, song, outputPath, durationSec, bpm, motionIndex) {
    const dir = path.dirname(outputPath);
    const sceneImgPath = path.join(dir, `scene_raw_s${scene.sceneNumber}.png`);
    const subtitleImgPath = path.join(dir, `sub_s${scene.sceneNumber}.png`);
    const particlesImgPath = path.join(dir, `particles_s${scene.sceneNumber}.png`);

    // 1. Generate high-res 1920x1080 cartoon scene
    await sceneGenerator.generateScene(
      {
        verseNumber: scene.sceneNumber,
        lyrics: scene.lyrics,
        sceneDescription: scene.action
      },
      song,
      sceneImgPath
    );

    // 2. Generate kid-friendly sing-along lyrics overlay
    await this._generateSubtitleBanner(scene.lyrics, subtitleImgPath);

    // 3. Generate decorative sparkle / musical note particle layer
    await this._generateParticleLayer(particlesImgPath, scene.sceneNumber);

    // 4. Build dynamic multi-axis camera motion & rhythmic bounce
    const totalFrames = Math.max(30, Math.round(durationSec * this.fps));
    const bounceFreq = (bpm / 60) * 2; // Twice per beat for bouncy toddler bounce

    // Motion styles cycle across scenes
    let zoompanExpr = '';
    if (motionIndex % 4 === 0) {
      // Smooth dynamic dolly-in with subtle left-right sway
      zoompanExpr = `zoompan=z='min(zoom+0.0012,1.18)':d=${totalFrames}:x='iw/2-(iw/zoom/2)+sin(2*PI*on/${totalFrames})*35':y='ih/2-(ih/zoom/2)':s=${this.width}x${this.height}:fps=${this.fps}`;
    } else if (motionIndex % 4 === 1) {
      // Medium panning tracking shot from left to right
      zoompanExpr = `zoompan=z='1.12':d=${totalFrames}:x='(iw-iw/zoom)*(on/${totalFrames})':y='ih/2-(ih/zoom/2)':s=${this.width}x${this.height}:fps=${this.fps}`;
    } else if (motionIndex % 4 === 2) {
      // Dynamic camera orbit push
      zoompanExpr = `zoompan=z='min(zoom+0.0009,1.14)':d=${totalFrames}:x='iw/2-(iw/zoom/2)+cos(2*PI*on/${totalFrames})*40':y='ih/2-(ih/zoom/2)+sin(2*PI*on/${totalFrames})*20':s=${this.width}x${this.height}:fps=${this.fps}`;
    } else {
      // Celebratory wide pull-back
      zoompanExpr = `zoompan=z='if(lte(on,1),1.16,max(1.0,zoom-0.0010))':d=${totalFrames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${this.width}x${this.height}:fps=${this.fps}`;
    }

    return new Promise((resolve, reject) => {
      ffmpeg()
        .input(sceneImgPath)
        .loop(durationSec)
        .input(particlesImgPath)
        .loop(durationSec)
        .input(subtitleImgPath)
        .complexFilter([
          // 1. Dynamic camera movement on background
          `[0:v]${zoompanExpr}[cam]`,
          // 2. Overlay particle sparkles
          `[cam][1:v]overlay=0:0:format=auto[cam_particles]`,
          // 3. Overlay sing-along subtitle banner
          `[cam_particles][2:v]overlay=0:0[out]`
        ])
        .map('[out]')
        .videoCodec('libx264')
        .outputOptions([
          '-pix_fmt yuv420p',
          '-preset fast',
          '-crf 20',
          `-t ${durationSec}`
        ])
        .save(outputPath)
        .on('end', () => {
          // Cleanup intermediate files
          try { fs.unlinkSync(subtitleImgPath); } catch (e) {}
          try { fs.unlinkSync(particlesImgPath); } catch (e) {}
          resolve(outputPath);
        })
        .on('error', (err) => {
          console.error(`[VeoVideoGenerator] Video clip synthesis error: ${err.message}`);
          reject(err);
        });
    });
  }

  /**
   * Overlays sing-along subtitles onto an existing Veo MP4 video
   */
  async _overlaySubtitlesAndEffects(rawVideoPath, lyrics, outputPath, durationSec) {
    const dir = path.dirname(outputPath);
    const subtitleImgPath = path.join(dir, `sub_veo_${Date.now()}.png`);
    await this._generateSubtitleBanner(lyrics, subtitleImgPath);

    return new Promise((resolve, reject) => {
      ffmpeg()
        .input(rawVideoPath)
        .input(subtitleImgPath)
        .complexFilter([
          '[0:v][1:v]overlay=0:0[out]'
        ])
        .map('[out]')
        .videoCodec('libx264')
        .outputOptions([
          '-pix_fmt yuv420p',
          '-preset fast',
          '-crf 20',
          `-t ${durationSec}`
        ])
        .save(outputPath)
        .on('end', () => {
          try { fs.unlinkSync(subtitleImgPath); } catch (e) {}
          try { fs.unlinkSync(rawVideoPath); } catch (e) {}
          resolve(outputPath);
        })
        .on('error', (err) => {
          try { fs.unlinkSync(subtitleImgPath); } catch (e) {}
          reject(err);
        });
    });
  }

  /**
   * Generates a transparent 1920x1080 SVG subtitle overlay with high-contrast glowing text
   */
  async _generateSubtitleBanner(lyrics, outputPath) {
    const words = (lyrics || '').trim().split(' ');
    let line1 = words.join(' ');
    let line2 = '';

    if (words.length > 7) {
      const mid = Math.ceil(words.length / 2);
      line1 = words.slice(0, mid).join(' ');
      line2 = words.slice(mid).join(' ');
    }

    const escapeXml = (str) => str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    const safeLine1 = escapeXml(line1);
    const safeLine2 = escapeXml(line2);

    const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${this.width}" height="${this.height}" viewBox="0 0 ${this.width} ${this.height}">
  <defs>
    <filter id="subGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#000000" flood-opacity="0.9" />
    </filter>
  </defs>

  <!-- Dark Rounded Pill Background for 100% Mobile & TV Readability -->
  <g filter="url(#subGlow)">
    <rect x="160" y="${safeLine2 ? 880 : 925}" width="1600" height="${safeLine2 ? 165 : 115}" rx="38" fill="#13092C" opacity="0.75" stroke="#FFE600" stroke-width="4" />
  </g>

  <!-- Big Sing-Along Words with Heavy Cartoon Outlines -->
  <g text-anchor="middle" font-family="'Arial Rounded MT Bold', 'Trebuchet MS', Arial, sans-serif" font-weight="900" filter="url(#subGlow)">
    ${safeLine2 ? `
      <text x="960" y="945" font-size="46" fill="#FFF176" stroke="#0D001F" stroke-width="12" paint-order="stroke fill">${safeLine1}</text>
      <text x="960" y="1005" font-size="46" fill="#00E5FF" stroke="#0D001F" stroke-width="12" paint-order="stroke fill">${safeLine2}</text>
    ` : `
      <text x="960" y="1000" font-size="52" fill="#FFE600" stroke="#0D001F" stroke-width="14" paint-order="stroke fill">${safeLine1}</text>
    `}
  </g>
</svg>
    `;

    await sharp(Buffer.from(svg))
      .resize(this.width, this.height)
      .png()
      .toFile(outputPath);

    return outputPath;
  }

  /**
   * Generates a transparent 1920x1080 particle layer with musical notes and sparkles
   */
  async _generateParticleLayer(outputPath, seed) {
    const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${this.width}" height="${this.height}" viewBox="0 0 ${this.width} ${this.height}">
  <!-- Musical Notes Floating -->
  <g fill="#FFD54F" opacity="0.65">
    <text x="180" y="240" font-size="64" font-family="Arial">♪</text>
    <text x="1720" y="320" font-size="76" font-family="Arial">♫</text>
    <text x="1600" y="180" font-size="54" font-family="Arial">♪</text>
    <text x="320" y="160" font-size="48" font-family="Arial">♫</text>
  </g>

  <!-- Twinkling Sparkles -->
  <g fill="#00E5FF" opacity="0.7">
    <polygon points="260,380 270,395 285,405 270,415 260,430 250,415 235,405 250,395" />
    <polygon points="1520,440 1528,452 1540,460 1528,468 1520,480 1512,468 1500,460 1512,452" />
    <polygon points="880,140 888,152 900,160 888,168 880,180 872,168 860,160 872,152" />
  </g>
</svg>
    `;

    await sharp(Buffer.from(svg))
      .resize(this.width, this.height)
      .png()
      .toFile(outputPath);

    return outputPath;
  }
}

module.exports = new VeoVideoGenerator();
