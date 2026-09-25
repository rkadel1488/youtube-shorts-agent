const ffmpeg = require('fluent-ffmpeg');
const ffmpegPath = require('ffmpeg-static');
const sharp = require('sharp');
const fs = require('fs');
const path = require('path');
const config = require('../../config');
ffmpeg.setFfmpegPath(ffmpegPath);

/**
 * 3D Cartoon Animator & Clip Generator
 * Transforms cartoon scenes into dynamic animated video clips with Ken Burns camera motion,
 * subtle cartoon rhythm bounce, and chunky sing-along lyric subtitle overlays.
 */
class CartoonAnimator {
  constructor() {
    this.fps = config.video.fps || 30;
    this.width = config.video.width || 1920;
    this.height = config.video.height || 1080;
  }

  /**
   * Generates an animated video clip for a single verse
   * @param {string} sceneImagePath 1920x1080 PNG
   * @param {number} durationSec Duration in seconds
   * @param {string} lyricsText Sing-along lyrics text
   * @param {string} outputPath Target .mp4 file
   * @param {Object} options Camera motion style, verse number
   */
  async createVerseClip(sceneImagePath, durationSec, lyricsText, outputPath, options = {}) {
    const dir = path.dirname(outputPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    // 1. Generate transparent 1920x1080 subtitle banner with chunky cartoon typography
    const subtitleOverlayPath = path.join(dir, `sub_${path.basename(outputPath, '.mp4')}.png`);
    await this._generateSubtitleBanner(lyricsText, subtitleOverlayPath);

    // 2. Build FFmpeg command with Ken Burns zoom and subtitle overlay
    const totalFrames = Math.max(30, Math.round(durationSec * this.fps));
    const motionStyle = options.motionIndex || 0;

    // Alternate camera directions for visual variety
    let zoomFilter = '';
    if (motionStyle % 3 === 0) {
      // Slow gentle zoom IN toward center
      zoomFilter = `zoompan=z='min(zoom+0.0010,1.15)':d=${totalFrames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${this.width}x${this.height}:fps=${this.fps}`;
    } else if (motionStyle % 3 === 1) {
      // Gentle pan LEFT to RIGHT with slight zoom
      zoomFilter = `zoompan=z='1.10':d=${totalFrames}:x='if(lte(on,1),(iw-iw/zoom)/2,x+0.5)':y='ih/2-(ih/zoom/2)':s=${this.width}x${this.height}:fps=${this.fps}`;
    } else {
      // Gentle zoom OUT from close-up
      zoomFilter = `zoompan=z='if(lte(on,1),1.14,max(1.0,zoom-0.0008))':d=${totalFrames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${this.width}x${this.height}:fps=${this.fps}`;
    }

    return new Promise((resolve, reject) => {
      ffmpeg()
        .input(sceneImagePath)
        .loop(durationSec)
        .input(subtitleOverlayPath)
        .complexFilter([
          `[0:v]${zoomFilter}[bg]`,
          `[bg][1:v]overlay=0:0[out]`
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
          // Clean up temp subtitle png
          try { fs.unlinkSync(subtitleOverlayPath); } catch (e) {}
          resolve(outputPath);
        })
        .on('error', (err) => {
          console.error('[CartoonAnimator] Clip rendering error:', err.message);
          reject(err);
        });
    });
  }

  /**
   * Generates a 1920x1080 transparent PNG with kid-friendly bubble sing-along lyrics
   */
  async _generateSubtitleBanner(lyrics, outputPath) {
    // Break lyrics into 1 or 2 lines if long
    const words = (lyrics || '').trim().split(' ');
    let line1 = words.join(' ');
    let line2 = '';

    if (words.length > 7) {
      const mid = Math.ceil(words.length / 2);
      line1 = words.slice(0, mid).join(' ');
      line2 = words.slice(mid).join(' ');
    }

    // Escape XML special characters
    const escapeXml = (str) => str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    const safeLine1 = escapeXml(line1);
    const safeLine2 = escapeXml(line2);

    const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${this.width}" height="${this.height}" viewBox="0 0 ${this.width} ${this.height}">
  <defs>
    <filter id="textGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="6" stdDeviation="6" flood-color="#000000" flood-opacity="0.85" />
    </filter>
  </defs>

  <!-- Semi-Transparent Dark Rounded Backing Pill for 100% Readability -->
  <g filter="url(#textGlow)">
    <rect x="160" y="${safeLine2 ? 880 : 930}" width="1600" height="${safeLine2 ? 160 : 110}" rx="35" fill="#1A0A38" opacity="0.65" stroke="#FFE600" stroke-width="4" />
  </g>

  <!-- Sing-Along Lyrics with Heavy Cartoon Outline -->
  <g text-anchor="middle" font-family="'Arial Rounded MT Bold', 'Trebuchet MS', Arial, sans-serif" font-weight="900" filter="url(#textGlow)">
    ${safeLine2 ? `
      <!-- 2-Line Mode -->
      <text x="960" y="945" font-size="46" fill="#FFF176" stroke="#12002B" stroke-width="12" paint-order="stroke fill">${safeLine1}</text>
      <text x="960" y="1005" font-size="46" fill="#00E5FF" stroke="#12002B" stroke-width="12" paint-order="stroke fill">${safeLine2}</text>
    ` : `
      <!-- 1-Line Mode -->
      <text x="960" y="1000" font-size="52" fill="#FFE600" stroke="#12002B" stroke-width="14" paint-order="stroke fill">${safeLine1}</text>
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
   * Combines multiple verse clips with the master song audio into a full song video
   * @param {Array<string>} clipPaths Array of verse .mp4 file paths
   * @param {string} audioPath Master song .mp3 audio
   * @param {string} outputPath Output .mp4 video file
   */
  async stitchSongVideo(clipPaths, audioPath, outputPath) {
    const dir = path.dirname(outputPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    // Create a concat text file for FFmpeg concat demuxer
    const concatListPath = path.join(dir, `concat_${Date.now()}.txt`);
    const fileContent = clipPaths.map(p => `file '${p.replace(/\\/g, '/')}'`).join('\n');
    fs.writeFileSync(concatListPath, fileContent);

    return new Promise((resolve, reject) => {
      ffmpeg()
        .input(concatListPath)
        .inputOptions(['-f concat', '-safe 0'])
        .input(audioPath)
        .outputOptions([
          '-c:v copy',
          '-c:a aac',
          '-b:a 192k',
          '-shortest'
        ])
        .save(outputPath)
        .on('end', () => {
          try { fs.unlinkSync(concatListPath); } catch (e) {}
          resolve(outputPath);
        })
        .on('error', (err) => {
          try { fs.unlinkSync(concatListPath); } catch (e) {}
          console.error('[CartoonAnimator] Song stitching error:', err.message);
          reject(err);
        });
    });
  }
}

module.exports = new CartoonAnimator();
