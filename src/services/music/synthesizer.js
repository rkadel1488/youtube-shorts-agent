const fs = require('fs');
const path = require('path');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegPath = require('ffmpeg-static');
const config = require('../../config');
ffmpeg.setFfmpegPath(ffmpegPath);

/**
 * Trending Kids Pop & Nursery Music Synthesizer
 * Generates modern, upbeat, 124 BPM toddler dance tracks inspired by YouTube trending kids music
 * (Cocomelon, Super Simple Songs, Baby Shark style).
 * Features:
 * - 4-on-the-floor punchy kick & crisp toddler handclaps
 * - 16th-note shaker/tambourine rhythm section
 * - Ukulele / acoustic guitar offbeat reggae/pop skank strums
 * - Bouncy funk bassline with toddler bopping groove
 * - Sparkling glockenspiel / xylophone hook melodies
 * - Seamless support for external royalty-free tracks from assets/audio/trending_music/
 */
class NurserySynthesizer {
  constructor() {
    this.sampleRate = 44100;
    this.trendingMusicDir = path.join(config.paths.assets, 'audio', 'trending_music');
    if (!fs.existsSync(this.trendingMusicDir)) {
      fs.mkdirSync(this.trendingMusicDir, { recursive: true });
    }
  }

  /**
   * Generates or loads an instrumental backing track for a song
   * @param {string} outputPath Destination file path (.wav)
   * @param {number} durationSec Length in seconds
   * @param {string} style 'trending_pop' | 'bounce' | 'adventure' | 'learning' | 'lullaby'
   * @param {number} bpm Beats per minute (default: 124)
   */
  async generateBackingTrack(outputPath, durationSec = 30, style = 'trending_pop', bpm = 124) {
    const dir = path.dirname(outputPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    // 1. Check if user placed a custom copyright-free audio track in assets/audio/trending_music/
    const customTrack = this._findCustomTrendingTrack(style);
    if (customTrack) {
      console.log(`🎵 [Trending Music] Using royalty-free backing track: ${path.basename(customTrack)}`);
      return await this._adaptCustomTrack(customTrack, durationSec, outputPath);
    }

    // 2. Synthesize modern Trending Kids Pop audio track
    return this._synthesizeTrendingPopTrack(outputPath, durationSec, style, bpm);
  }

  _findCustomTrendingTrack(style) {
    if (!fs.existsSync(this.trendingMusicDir)) return null;
    const files = fs.readdirSync(this.trendingMusicDir).filter(f => f.endsWith('.mp3') || f.endsWith('.wav'));
    if (files.length === 0) return null;

    // Look for matching style or take the first available
    const matched = files.find(f => f.toLowerCase().includes(style.toLowerCase()));
    return path.join(this.trendingMusicDir, matched || files[0]);
  }

  async _adaptCustomTrack(trackPath, durationSec, outputPath) {
    return new Promise((resolve, reject) => {
      ffmpeg(trackPath)
        .inputOptions([`-stream_loop -1`]) // Loop continuously
        .outputOptions([
          `-t ${durationSec}`,
          '-af', `afade=t=in:ss=0:d=1.0,afade=t=out:st=${Math.max(0, durationSec - 2)}:d=2.0`
        ])
        .audioCodec('pcm_s16le')
        .save(outputPath)
        .on('end', () => resolve(outputPath))
        .on('error', reject);
    });
  }

  _synthesizeTrendingPopTrack(outputPath, durationSec, style, bpm) {
    const sampleRate = this.sampleRate;
    const numChannels = 2; // Stereo
    const totalSamples = Math.floor(durationSec * sampleRate);
    const buffer = Buffer.alloc(44 + totalSamples * numChannels * 2);

    // RIFF Header
    buffer.write('RIFF', 0);
    buffer.writeUInt32LE(36 + totalSamples * numChannels * 2, 4);
    buffer.write('WAVE', 8);
    buffer.write('fmt ', 12);
    buffer.writeUInt32LE(16, 16);
    buffer.writeUInt16LE(1, 20); // PCM format
    buffer.writeUInt16LE(numChannels, 22);
    buffer.writeUInt32LE(sampleRate, 24);
    buffer.writeUInt32LE(sampleRate * numChannels * 2, 28);
    buffer.writeUInt16LE(numChannels * 2, 32);
    buffer.writeUInt16LE(16, 34); // 16 bits per sample
    buffer.write('data', 36);
    buffer.writeUInt32LE(totalSamples * numChannels * 2, 40);

    // 1. World-famous Top-40 Kids Pop Chord Progression (I - V - vi - IV):
    // C Major -> G Major -> A Minor -> F Major
    const popChords = [
      [261.63, 329.63, 392.00], // C major (C4, E4, G4)
      [392.00, 493.88, 587.33], // G major (G4, B4, D5)
      [220.00, 261.63, 329.63], // A minor (A3, C4, E4)
      [349.23, 440.00, 523.25]  // F major (F4, A4, C5)
    ];

    // Cheerful Bounce (C - F - G - C)
    const bounceChords = [
      [261.63, 329.63, 392.00], // C
      [349.23, 440.00, 523.25], // F
      [392.00, 493.88, 587.33], // G
      [261.63, 329.63, 523.25]  // C
    ];

    // Lullaby Progression
    const lullabyChords = [
      [261.63, 329.63, 392.00], // C
      [220.00, 261.63, 329.63], // Am
      [349.23, 440.00, 523.25], // F
      [392.00, 493.88, 587.33]  // G
    ];

    let activeChords = popChords;
    let effectiveBpm = bpm || 124;

    if (style === 'lullaby') {
      activeChords = lullabyChords;
      effectiveBpm = 75;
    } else if (style === 'bounce') {
      activeChords = bounceChords;
      effectiveBpm = 120;
    }

    const beatSec = 60 / effectiveBpm;
    let offset = 44;

    for (let i = 0; i < totalSamples; i++) {
      const t = i / sampleRate;
      const beat = t / beatSec;
      const chordIndex = Math.floor(beat / 4) % activeChords.length;
      const currentChord = activeChords[chordIndex];
      const beatFract = beat % 1;

      // -------------------------------------------------------------
      // 1. DRUMS & PERCUSSION SECTION
      // -------------------------------------------------------------
      let kick = 0;
      let handclap = 0;
      let shaker = 0;

      if (style !== 'lullaby') {
        // Four-on-the-floor punchy kick (every beat: 1, 2, 3, 4)
        if (beatFract < 0.16) {
          const kickFreq = 120 * Math.exp(-beatFract * 26);
          kick = Math.sin(2 * Math.PI * kickFreq * t) * Math.exp(-beatFract * 16) * 0.38;
        }

        // Snappy Toddler Handclaps on beats 2 and 4
        const beatNumInBar = Math.floor(beat % 4);
        const isClapBeat = (beatNumInBar === 1 || beatNumInBar === 3);
        if (isClapBeat && beatFract < 0.14) {
          handclap = (Math.random() * 2 - 1) * Math.exp(-beatFract * 36) * 0.24;
        }

        // 16th-Note Shaker / Tambourine Sizzle
        const sixteenthFract = (beat * 4) % 1;
        if (sixteenthFract < 0.05) {
          shaker = (Math.random() * 2 - 1) * Math.exp(-sixteenthFract * 60) * 0.08;
        }
      }

      // -------------------------------------------------------------
      // 2. UKULELE / ACOUSTIC OFFBEAT STRUM (The signature kids pop sunshine vibe!)
      // -------------------------------------------------------------
      let ukeStrum = 0;
      if (style !== 'lullaby') {
        // Offbeat strum on the "&" of the beat (0.5 to 0.75)
        const offbeatDist = beatFract - 0.5;
        if (offbeatDist >= 0 && offbeatDist < 0.22) {
          const ukeDecay = Math.exp(-offbeatDist * 18);
          // Play triad chord with bright acoustic timbre
          ukeStrum = (
            Math.sin(2 * Math.PI * currentChord[0] * 2 * t) * 0.4 +
            Math.sin(2 * Math.PI * currentChord[1] * 2 * t) * 0.35 +
            Math.sin(2 * Math.PI * currentChord[2] * 2 * t) * 0.25
          ) * ukeDecay * 0.18;
        }
      }

      // -------------------------------------------------------------
      // 3. BOUNCY TODDLER FUNK BASSLINE
      // -------------------------------------------------------------
      let bass = 0;
      const rootNote = currentChord[0] / 2;
      const fifthNote = currentChord[2] / 2;
      // Walking bass pattern: Root on 1, 5th on 2.5, Root on 3
      const bassNote = (beatFract > 0.5 && Math.floor(beat % 2) === 0) ? fifthNote : rootNote;
      const bassDecay = (style === 'lullaby') ? Math.exp(-(beat % 2) * 1.5) : Math.exp(-(beatFract % 0.5) * 6);
      bass = (
        Math.sin(2 * Math.PI * bassNote * t) * 0.75 +
        Math.sin(2 * Math.PI * bassNote * 2 * t) * 0.25
      ) * bassDecay * ((style === 'lullaby') ? 0.16 : 0.30);

      // -------------------------------------------------------------
      // 4. GLOCKENSPIEL / XYLOPHONE SPARKLE LEAD
      // -------------------------------------------------------------
      const arpeggioSpeed = (style === 'lullaby') ? 1 : 2;
      const noteInBeat = Math.floor(beat * arpeggioSpeed) % currentChord.length;
      const chimeBase = currentChord[noteInBeat];
      const chimeFreq = chimeBase * 2;
      const noteTime = (beat * arpeggioSpeed) % 1;
      const chimeDecay = (style === 'lullaby') ? 3.5 : 5.5;
      const chimeEnv = Math.exp(-noteTime * chimeDecay);

      // Bell harmonics
      const glockenspiel = (
        Math.sin(2 * Math.PI * chimeFreq * t) * 0.65 +
        Math.sin(2 * Math.PI * chimeFreq * 2.01 * t) * 0.25 +
        Math.sin(2 * Math.PI * chimeFreq * 3.02 * t) * 0.10
      ) * chimeEnv * 0.25;

      // -------------------------------------------------------------
      // 5. MASTER MIX & STEREO IMAGING
      // -------------------------------------------------------------
      let masterGain = 1.0;
      if (t < 1.2) masterGain = t / 1.2; // Fade-in
      if (t > durationSec - 2.0) masterGain = Math.max(0, (durationSec - t) / 2.0); // Fade-out

      const left = (glockenspiel * 1.05 + ukeStrum * 1.1 + bass * 0.95 + kick * 1.0 + handclap * 0.9 + shaker * 0.8) * masterGain;
      const right = (glockenspiel * 0.95 + ukeStrum * 0.9 + bass * 1.05 + kick * 1.0 + handclap * 1.1 + shaker * 1.2) * masterGain;

      const clampedL = Math.max(-1, Math.min(1, left));
      const clampedR = Math.max(-1, Math.min(1, right));

      buffer.writeInt16LE(Math.floor(clampedL * 32767), offset);
      buffer.writeInt16LE(Math.floor(clampedR * 32767), offset + 2);
      offset += 4;
    }

    fs.writeFileSync(outputPath, buffer);
    return outputPath;
  }
}

module.exports = new NurserySynthesizer();
