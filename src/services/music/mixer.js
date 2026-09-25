const ffmpeg = require('fluent-ffmpeg');
const ffmpegPath = require('ffmpeg-static');
const path = require('path');
const fs = require('fs');
const synthesizer = require('./synthesizer');
ffmpeg.setFfmpegPath(ffmpegPath);

/**
 * Audio Mixer & Master Producer
 * Combines vocals and instrumental backing tracks with ducking and YouTube standard normalization.
 */
class AudioMixer {
  /**
   * Produces the complete song audio track
   * @param {Object} params { vocalPath, totalDurationSec, song, outputDir }
   */
  async produceSongAudio(params) {
    const { vocalPath, totalDurationSec, song, outputDir } = params;
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

    // 1. Generate synthesized instrumental backing track matching the duration and style
    const backingTrackPath = path.join(outputDir, 'backing_track.wav');
    await synthesizer.generateBackingTrack(
      backingTrackPath,
      totalDurationSec,
      song.musicalStyle || 'bounce',
      song.bpm || 115
    );

    // 2. Mix vocals + backing track with ducking and volume balance
    const finalAudioPath = path.join(outputDir, 'song_master.mp3');

    return new Promise((resolve, reject) => {
      ffmpeg()
        .input(backingTrackPath)
        .input(vocalPath)
        .complexFilter([
          // BGM volume reduced to 0.35, vocal boosted to 1.35
          '[0:a]volume=0.35[bgm]',
          '[1:a]volume=1.35[vox]',
          // Combine both streams
          '[bgm][vox]amix=inputs=2:duration=first:dropout_transition=2[mixed]',
          // Normalize audio for YouTube loudness (-14 LUFS target)
          '[mixed]loudnorm=I=-14:LRA=7:tp=-1.5[out]'
        ])
        .map('[out]')
        .audioCodec('libmp3lame')
        .audioBitrate(192)
        .save(finalAudioPath)
        .on('end', () => {
          resolve({
            audioPath: finalAudioPath,
            backingTrackPath: backingTrackPath,
            durationSec: totalDurationSec
          });
        })
        .on('error', (err) => {
          // If loudnorm filter fails on some minimal streams, fallback to simple mix
          console.warn('[AudioMixer] Loudnorm filter warning, falling back to volume mix:', err.message);
          this._fallbackMix(backingTrackPath, vocalPath, finalAudioPath)
            .then(resolve)
            .catch(reject);
        });
    });
  }

  /**
   * Fallback mix if complex loudnorm encounters platform quirks
   */
  _fallbackMix(bgmPath, voxPath, outPath) {
    return new Promise((resolve, reject) => {
      ffmpeg()
        .input(bgmPath)
        .input(voxPath)
        .complexFilter([
          '[0:a]volume=0.32[bgm]',
          '[1:a]volume=1.3[vox]',
          '[bgm][vox]amix=inputs=2:duration=first:dropout_transition=2[out]'
        ])
        .map('[out]')
        .audioCodec('libmp3lame')
        .audioBitrate(192)
        .save(outPath)
        .on('end', () => resolve({ audioPath: outPath }))
        .on('error', reject);
    });
  }
}

module.exports = new AudioMixer();
