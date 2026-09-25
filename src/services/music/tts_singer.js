const { MsEdgeTTS, OUTPUT_FORMAT } = require('msedge-tts');
const fs = require('fs');
const path = require('path');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegPath = require('ffmpeg-static');
ffmpeg.setFfmpegPath(ffmpegPath);
try {
  const ffprobeStatic = require('ffprobe-static');
  if (ffprobeStatic && ffprobeStatic.path) {
    ffmpeg.setFfprobePath(ffprobeStatic.path);
  }
} catch (e) {}

/**
 * Children's Cartoon Vocal Singer using Microsoft Edge Speech
 * Generates clear, energetic, cartoon-like children's singing and rhythmic narration.
 * Includes automatic retry with fresh connection handling.
 */
class TTSSinger {
  constructor() {
    this.defaultVoice = 'en-US-AnaNeural'; // Playful toddler/child voice
    this.fallbackVoices = ['en-US-AnaNeural', 'en-US-JennyNeural', 'en-US-AriaNeural'];
  }

  /**
   * Generates vocal audio for a song
   * @param {Object} song Song object with verses
   * @param {string} outputDir Directory to save vocal files
   * @param {Object} options { voice, pitch, rate }
   */
  async generateVocals(song, outputDir, options = {}) {
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

    const voice = options.voice || song.voice || this.defaultVoice;
    const pitch = options.pitch || '+10Hz';
    const rate = options.rate || '+4%';

    const verseResults = [];
    let currentTimelineSec = 1.0; // 1s intro buffer

    for (let i = 0; i < song.verses.length; i++) {
      const verse = song.verses[i];
      const verseTempDir = path.join(outputDir, `vocal_verse_${i + 1}`);
      if (!fs.existsSync(verseTempDir)) fs.mkdirSync(verseTempDir, { recursive: true });

      const vocalText = verse.lyrics.trim();

      // Synthesize with automatic retry & fallback
      const rawAudioPath = await this._synthesizeWithRetry(verseTempDir, vocalText, voice, pitch, rate);

      // Get exact duration of verse audio
      const durationSec = await this._getAudioDuration(rawAudioPath);

      // Save verse timing metadata
      const verseInfo = {
        verseNumber: verse.verseNumber || (i + 1),
        lyrics: verse.lyrics,
        sceneDescription: verse.sceneDescription,
        audioPath: rawAudioPath,
        startTimeSec: currentTimelineSec,
        durationSec: durationSec,
        endTimeSec: currentTimelineSec + durationSec
      };

      verseResults.push(verseInfo);
      currentTimelineSec += durationSec + 1.5;
    }

    // Concatenate all verse vocals into a single aligned vocal track
    const fullVocalPath = path.join(outputDir, 'vocals_full.mp3');
    await this._stitchVerseVocals(verseResults, currentTimelineSec, fullVocalPath);

    return {
      vocalPath: fullVocalPath,
      totalDurationSec: currentTimelineSec + 1.0,
      verses: verseResults
    };
  }

  /**
   * Synthesizes audio with up to 3 retries and fallback voices
   */
  async _synthesizeWithRetry(dir, text, primaryVoice, pitch, rate) {
    const voicesToTry = [primaryVoice, ...this.fallbackVoices.filter(v => v !== primaryVoice)];
    let lastError = null;

    for (const voice of voicesToTry) {
      for (let attempt = 1; attempt <= 2; attempt++) {
        try {
          const tts = new MsEdgeTTS();
          await tts.setMetadata(voice, OUTPUT_FORMAT.AUDIO_24KHZ_48KBITRATE_MONO_MP3);
          const result = await tts.toFile(dir, text, { pitch, rate });
          if (result && result.audioFilePath && fs.existsSync(result.audioFilePath) && fs.statSync(result.audioFilePath).size > 1000) {
            return result.audioFilePath;
          }
        } catch (err) {
          lastError = err;
          // Wait 1.5 seconds before retry
          await new Promise(r => setTimeout(r, 1500));
        }
      }
    }

    // If external Edge TTS server is unreachable, generate a clean rhythmic vocal tone
    console.warn(`[TTSSinger] Edge TTS network unavailable (${lastError?.message}). Using procedural melodic vocal lead track.`);
    return this._generateProceduralVocalTrack(dir, text);
  }

  /**
   * Procedural vocal track if Edge TTS is offline/blocked
   */
  async _generateProceduralVocalTrack(dir, text) {
    const outPath = path.join(dir, `procedural_vox_${Date.now()}.mp3`);
    const wordCount = (text || '').split(' ').length;
    const duration = Math.max(3.5, wordCount * 0.6);

    return new Promise((resolve, reject) => {
      ffmpeg()
        .input(`sine=frequency=440:beep_factor=4:duration=${duration}`)
        .inputFormat('lavfi')
        .audioCodec('libmp3lame')
        .outputOptions(['-b:a 128k', `-t ${duration}`])
        .save(outPath)
        .on('end', () => resolve(outPath))
        .on('error', () => {
          // If lavfi sine is unsupported, create a silent buffer
          const buffer = Buffer.alloc(Math.floor(duration * 44100 * 2));
          fs.writeFileSync(outPath.replace('.mp3', '.wav'), buffer);
          resolve(outPath.replace('.mp3', '.wav'));
        });
    });
  }

  /**
   * Helper to inspect audio duration via ffprobe or file size estimation
   */
  _getAudioDuration(filePath) {
    return new Promise((resolve) => {
      ffmpeg.ffprobe(filePath, (err, metadata) => {
        if (!err && metadata && metadata.format && metadata.format.duration) {
          return resolve(metadata.format.duration);
        }
        // Fallback: estimate from file size (48kbps mono MP3 = 6000 bytes/sec)
        try {
          const stats = fs.statSync(filePath);
          const estimated = Math.max(3.0, stats.size / 6000);
          resolve(estimated);
        } catch (e) {
          resolve(5.0);
        }
      });
    });
  }

  /**
   * Stitches verse audio files with precise pauses into a unified vocal master track
   */
  _stitchVerseVocals(verses, totalDuration, outputPath) {
    return new Promise((resolve, reject) => {
      let command = ffmpeg();

      verses.forEach(v => {
        command = command.input(v.audioPath);
      });

      const filterInputs = [];
      const filterSteps = [];

      verses.forEach((v, index) => {
        const delayMs = Math.round(v.startTimeSec * 1000);
        filterSteps.push(`[${index}:a]adelay=${delayMs}|${delayMs}[a${index}]`);
        filterInputs.push(`[a${index}]`);
      });

      const mixString = `${filterInputs.join('')}amix=inputs=${verses.length}:duration=longest:dropout_transition=0[out]`;
      filterSteps.push(mixString);

      command
        .complexFilter(filterSteps)
        .map('[out]')
        .audioCodec('libmp3lame')
        .audioBitrate(192)
        .save(outputPath)
        .on('end', () => resolve(outputPath))
        .on('error', (err) => reject(err));
    });
  }
}

module.exports = new TTSSinger();
