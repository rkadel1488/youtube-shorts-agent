const ffmpeg = require('fluent-ffmpeg');
const ffmpegPath = require('ffmpeg-static');
const sharp = require('sharp');
const fs = require('fs');
const path = require('path');
const config = require('../../config');
ffmpeg.setFfmpegPath(ffmpegPath);

/**
 * Long-Form Video Compilation Engine
 * Combines multiple nursery rhyme cartoon videos into a cohesive 1080p long-form compilation.
 * Adds animated bumper intro cards between songs and generates YouTube SEO chapters with exact timestamps.
 */
class CompilationBuilder {
  constructor() {
    this.fps = config.video.fps || 30;
    this.width = config.video.width || 1920;
    this.height = config.video.height || 1080;
    this.bumperDuration = config.video.bumperDurationSec || 3.5;
  }

  /**
   * Compiles an array of rendered songs into a single long-form YouTube video
   * @param {Array<Object>} songProjects Array of completed song objects { title, videoPath, durationSec, ... }
   * @param {string} outputDir Output directory for master compilation
   * @param {string} compilationTitle Master compilation title
   */
  async buildCompilation(songProjects, outputDir, compilationTitle = 'Ultimate Nursery Rhymes Compilation') {
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

    const compilationId = `compilation_${Date.now()}`;
    const masterVideoPath = path.join(outputDir, `${compilationId}_master.mp4`);
    const chapters = [];
    const videoSegments = [];

    let currentTimelineSec = 0;

    // 1. Create Main Compilation Intro Bumper (3 seconds)
    const introBumperVideo = path.join(outputDir, 'intro_bumper.mp4');
    await this._createBumperCard(
      compilationTitle,
      '⭐ Non-Stop Sing-Along Fun for Kids! ⭐',
      '#FF1744',
      this.bumperDuration,
      introBumperVideo
    );
    videoSegments.push(introBumperVideo);

    chapters.push({
      timeSeconds: 0,
      timestamp: '00:00',
      title: 'Welcome & Sing-Along Intro 🎵'
    });
    currentTimelineSec += this.bumperDuration;

    // 2. Iterate through each song, add bumper & song video
    for (let i = 0; i < songProjects.length; i++) {
      const song = songProjects[i];

      // Add "Up Next" bumper card between songs (for songs after the first)
      if (i > 0) {
        const nextBumperPath = path.join(outputDir, `bumper_song_${i + 1}.mp4`);
        await this._createBumperCard(
          `Up Next: ${song.title}`,
          `Song ${i + 1} of ${songProjects.length} 🎶`,
          '#00B0FF',
          this.bumperDuration,
          nextBumperPath
        );
        videoSegments.push(nextBumperPath);
        currentTimelineSec += this.bumperDuration;
      }

      // Record chapter start
      const minutes = Math.floor(currentTimelineSec / 60).toString().padStart(2, '0');
      const seconds = Math.floor(currentTimelineSec % 60).toString().padStart(2, '0');
      chapters.push({
        timeSeconds: currentTimelineSec,
        timestamp: `${minutes}:${seconds}`,
        title: `${song.title} ${this._getEmojiForTheme(song.theme)}`
      });

      // Add actual song video
      videoSegments.push(song.videoPath);
      currentTimelineSec += song.durationSec;
    }

    // 3. Concatenate all video segments into the final master compilation
    await this._concatSegments(videoSegments, masterVideoPath);

    return {
      compilationId: compilationId,
      videoPath: masterVideoPath,
      totalDurationSec: currentTimelineSec,
      totalDurationFormatted: `${Math.floor(currentTimelineSec / 60)}m ${Math.floor(currentTimelineSec % 60)}s`,
      songCount: songProjects.length,
      chapters: chapters,
      songs: songProjects
    };
  }

  /**
   * Generates a cheerful cartoon bumper card video with audio chime
   */
  async _createBumperCard(title, subtitle, accentColor, durationSec, outputPath) {
    const dir = path.dirname(outputPath);
    const imagePath = path.join(dir, `bumper_${Date.now()}.png`);

    const escapeXml = (str) => (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    const safeTitle = escapeXml(title);
    const safeSubtitle = escapeXml(subtitle);

    const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${this.width}" height="${this.height}" viewBox="0 0 ${this.width} ${this.height}">
  <defs>
    <linearGradient id="bumperBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#311B92" />
      <stop offset="50%" stop-color="#512DA8" />
      <stop offset="100%" stop-color="#1A237E" />
    </linearGradient>

    <!-- Starburst Radial Gradient -->
    <radialGradient id="starburst" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#FFE57F" stop-opacity="0.9" />
      <stop offset="60%" stop-color="#FFD54F" stop-opacity="0.3" />
      <stop offset="100%" stop-color="#FFA000" stop-opacity="0" />
    </radialGradient>

    <filter id="cardShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="16" stdDeviation="16" flood-color="#000000" flood-opacity="0.6" />
    </filter>
  </defs>

  <!-- Background -->
  <rect width="${this.width}" height="${this.height}" fill="url(#bumperBg)" />
  <circle cx="960" cy="540" r="700" fill="url(#starburst)" />

  <!-- Confetti / Floating Music Notes -->
  <text x="320" y="320" font-size="90" fill="#FF4081">♫</text>
  <text x="1560" y="360" font-size="105" fill="#00E676">♪</text>
  <text x="400" y="820" font-size="80" fill="#FFD600">♪</text>
  <text x="1500" y="800" font-size="95" fill="#00E5FF">♫</text>

  <!-- Central Card -->
  <g transform="translate(260, 220)" filter="url(#cardShadow)">
    <rect x="0" y="0" width="1400" height="640" rx="60" fill="#FFFFFF" stroke="${accentColor}" stroke-width="16" />

    <!-- Ribbon / Badge -->
    <rect x="250" y="-35" width="900" height="90" rx="35" fill="${accentColor}" stroke="#FFFFFF" stroke-width="6" />
    <text x="700" y="24" font-family="'Arial Rounded MT Bold', Arial, sans-serif" font-weight="900" font-size="44" fill="#FFFFFF" text-anchor="middle">
      ${safeSubtitle}
    </text>

    <!-- Main Title -->
    <text x="700" y="330" font-family="'Arial Rounded MT Bold', Arial, sans-serif" font-weight="900" font-size="80" fill="#1A237E" text-anchor="middle">
      ${safeTitle}
    </text>

    <!-- Decorative Bottom Sparkle -->
    <text x="700" y="470" font-size="64" fill="#FFB300" text-anchor="middle">
      ✨ 👶 🎈 🎵 ✨
    </text>
  </g>
</svg>
    `;

    await sharp(Buffer.from(svg)).resize(this.width, this.height).png().toFile(imagePath);

    // Generate portable WAV chime audio (C5-E5-G5-C6 glockenspiel) - zero lavfi dependence
    const audioPath = path.join(dir, `bumper_aud_${Date.now()}.wav`);
    this._generateBumperChime(audioPath, durationSec);

    // Render bumper video clip
    return new Promise((resolve, reject) => {
      ffmpeg()
        .input(imagePath)
        .loop(durationSec)
        .input(audioPath)
        .outputOptions([
          '-c:v libx264',
          '-preset fast',
          '-pix_fmt yuv420p',
          '-r 30',
          '-c:a aac',
          '-b:a 192k',
          `-t ${durationSec}`,
          '-shortest'
        ])
        .save(outputPath)
        .on('end', () => {
          try { fs.unlinkSync(imagePath); } catch (e) {}
          try { fs.unlinkSync(audioPath); } catch (e) {}
          resolve(outputPath);
        })
        .on('error', (err) => {
          try { fs.unlinkSync(imagePath); } catch (e) {}
          try { fs.unlinkSync(audioPath); } catch (e) {}
          reject(err);
        });
    });
  }

  /**
   * Generates a 4-note glockenspiel chime in PCM WAV format
   */
  _generateBumperChime(outputPath, durationSec) {
    const sampleRate = 44100;
    const numChannels = 2;
    const totalSamples = Math.floor(durationSec * sampleRate);
    const buffer = Buffer.alloc(44 + totalSamples * numChannels * 2);

    buffer.write('RIFF', 0);
    buffer.writeUInt32LE(36 + totalSamples * numChannels * 2, 4);
    buffer.write('WAVE', 8);
    buffer.write('fmt ', 12);
    buffer.writeUInt32LE(16, 16);
    buffer.writeUInt16LE(1, 20); // PCM
    buffer.writeUInt16LE(numChannels, 22);
    buffer.writeUInt32LE(sampleRate, 24);
    buffer.writeUInt32LE(sampleRate * numChannels * 2, 28);
    buffer.writeUInt16LE(numChannels * 2, 32);
    buffer.writeUInt16LE(16, 34);
    buffer.write('data', 36);
    buffer.writeUInt32LE(totalSamples * numChannels * 2, 40);

    const freqs = [523.25, 659.25, 783.99, 1046.50]; // Joyful C5, E5, G5, C6 arpeggio
    let offset = 44;

    for (let i = 0; i < totalSamples; i++) {
      const t = i / sampleRate;
      let sample = 0;
      freqs.forEach((f, idx) => {
        const noteStart = idx * 0.22;
        if (t >= noteStart) {
          const noteTime = t - noteStart;
          sample += Math.sin(2 * Math.PI * f * noteTime) * Math.exp(-noteTime * 4.5) * 0.22;
        }
      });
      const clamped = Math.max(-1, Math.min(1, sample));
      const intVal = Math.floor(clamped * 32767);
      buffer.writeInt16LE(intVal, offset);
      buffer.writeInt16LE(intVal, offset + 2);
      offset += 4;
    }

    fs.writeFileSync(outputPath, buffer);
    return outputPath;
  }

  /**
   * Concatenates all video segments into the final master compilation
   */
  _concatSegments(segmentPaths, outputPath) {
    const dir = path.dirname(outputPath);
    const listPath = path.join(dir, `concat_master_${Date.now()}.txt`);
    const content = segmentPaths.map(p => `file '${p.replace(/\\/g, '/')}'`).join('\n');
    fs.writeFileSync(listPath, content);

    return new Promise((resolve, reject) => {
      ffmpeg()
        .input(listPath)
        .inputOptions(['-f concat', '-safe 0'])
        .outputOptions([
          '-c:v libx264',
          '-preset fast',
          '-crf 20',
          '-c:a aac',
          '-b:a 192k',
          '-pix_fmt yuv420p'
        ])
        .save(outputPath)
        .on('end', () => {
          try { fs.unlinkSync(listPath); } catch (e) {}
          resolve(outputPath);
        })
        .on('error', (err) => {
          try { fs.unlinkSync(listPath); } catch (e) {}
          reject(err);
        });
    });
  }

  _getEmojiForTheme(theme) {
    const map = {
      vehicles: '🚌',
      animals: '🐮',
      dinosaurs: '🦕',
      colors: '🎨',
      counting: '🦆',
      bedtime: '⭐',
      alphabet: '🔤',
      action_dance: '🎉'
    };
    return map[theme] || '🎵';
  }
}

module.exports = new CompilationBuilder();
