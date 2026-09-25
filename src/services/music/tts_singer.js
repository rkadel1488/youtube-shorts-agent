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
 */
class TTSSinger {
  constructor() {
    this.defaultVoice = 'en-US-AnaNeural'; // Playful toddler/child voice
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

    const tts = new MsEdgeTTS();
    await tts.setMetadata(voice, OUTPUT_FORMAT.AUDIO_24KHZ_48KBITRATE_MONO_MP3);

    const verseResults = [];
    let currentTimelineSec = 1.0; // 1s intro buffer

    for (let i = 0; i < song.verses.length; i++) {
      const verse = song.verses[i];
      const verseTempDir = path.join(outputDir, `vocal_verse_${i + 1}`);
      if (!fs.existsSync(verseTempDir)) fs.mkdirSync(verseTempDir, { recursive: true });

      // Clean lyrics for optimal singing cadence
      const vocalText = verse.lyrics.trim();

      // Synthesize verse audio
      const result = await tts.toFile(verseTempDir, vocalText, { pitch, rate });
      const rawAudioPath = result.audioFilePath;

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
      // Add a musical pause between verses (1.5 seconds)
      currentTimelineSec += durationSec + 1.5;
    }

    // Now concatenate all verse vocals into a single aligned vocal track
    const fullVocalPath = path.join(outputDir, 'vocals_full.mp3');
    await this._stitchVerseVocals(verseResults, currentTimelineSec, fullVocalPath);

    return {
      vocalPath: fullVocalPath,
      totalDurationSec: currentTimelineSec + 1.0, // extra trailing buffer
      verses: verseResults
    };
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

      // Input all verse audio files
      verses.forEach(v => {
        command = command.input(v.audioPath);
      });

      // Complex filter to delay each verse to its exact startTimeSec and mix together
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
