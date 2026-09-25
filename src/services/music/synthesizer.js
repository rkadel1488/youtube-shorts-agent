const fs = require('fs');
const path = require('path');

/**
 * Polyphonic Nursery Rhyme Instrumental Music Synthesizer
 * Generates cheerful, melodic WAV backing tracks with glockenspiel chimes, bass, and toddler beats.
 * Requires ZERO external API keys and runs instantly in Node.js.
 */
class NurserySynthesizer {
  constructor() {
    this.sampleRate = 44100;
  }

  /**
   * Generates an instrumental backing track for a nursery rhyme
   * @param {string} outputPath Destination file path (.wav)
   * @param {number} durationSec Length in seconds
   * @param {string} style 'bounce' | 'adventure' | 'learning' | 'lullaby'
   * @param {number} bpm Beats per minute (e.g. 115)
   */
  async generateBackingTrack(outputPath, durationSec = 30, style = 'bounce', bpm = 115) {
    const dir = path.dirname(outputPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

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

    // Nursery Major Key Progression (C - F - G - C)
    const chords = [
      [261.63, 329.63, 392.00], // C major (C4, E4, G4)
      [349.23, 440.00, 523.25], // F major (F4, A4, C5)
      [392.00, 493.88, 587.33], // G major (G4, B4, D5)
      [261.63, 329.63, 523.25]  // C major octave
    ];

    // Lullaby Progression (gentler, softer)
    const lullabyChords = [
      [261.63, 329.63, 392.00], // C
      [220.00, 261.63, 329.63], // Am
      [349.23, 440.00, 523.25], // F
      [392.00, 493.88, 587.33]  // G
    ];

    const activeChords = (style === 'lullaby') ? lullabyChords : chords;
    const actualBpm = (style === 'lullaby') ? Math.min(bpm, 80) : bpm;
    const beatSec = 60 / actualBpm;

    let offset = 44;

    for (let i = 0; i < totalSamples; i++) {
      const t = i / sampleRate;
      const beat = t / beatSec;
      const chordIndex = Math.floor(beat / 4) % activeChords.length;
      const currentChord = activeChords[chordIndex];

      // 1. Glockenspiel / Xylophone Arpeggio Melodic Chimes
      const arpeggioSpeed = (style === 'bounce' || style === 'learning') ? 2 : 1;
      const noteInBeat = Math.floor(beat * arpeggioSpeed) % currentChord.length;
      const baseNote = currentChord[noteInBeat];
      const octaveMult = (style === 'lullaby') ? 1.5 : 2.0;
      const chimeFreq = baseNote * octaveMult;
      const noteTime = (beat * arpeggioSpeed) % 1;
      const decayRate = (style === 'lullaby') ? 3.5 : 6.0;
      const chimeEnvelope = Math.exp(-noteTime * decayRate);

      // Bell harmonics (fundamental + subtle 2nd harmonic chime shimmer)
      const chime = (
        Math.sin(2 * Math.PI * chimeFreq * t) * 0.7 +
        Math.sin(2 * Math.PI * chimeFreq * 2.02 * t) * 0.2 +
        Math.sin(2 * Math.PI * chimeFreq * 3.01 * t) * 0.1
      ) * chimeEnvelope * 0.28;

      // 2. Playful Bouncy Bassline
      const bassFreq = currentChord[0] / 2;
      const bassDecay = (style === 'lullaby') ? Math.exp(-(beat % 2) * 1.5) : Math.exp(-(beat % 1) * 3.0);
      const bass = (
        Math.sin(2 * Math.PI * bassFreq * t) +
        0.35 * Math.sin(2 * Math.PI * bassFreq * 2 * t)
      ) * bassDecay * ((style === 'lullaby') ? 0.18 : 0.32);

      // 3. Cheerful Percussion (Snare/Handclap & Gentle Kick)
      let snare = 0;
      let kick = 0;
      if (style !== 'lullaby') {
        const beatFract = beat % 1;
        const isSnareBeat = (Math.floor(beat) % 2 === 1);
        if (isSnareBeat && beatFract < 0.12) {
          snare = (Math.random() * 2 - 1) * Math.exp(-beatFract * 32) * 0.16;
        }
        if (!isSnareBeat && beatFract < 0.18) {
          const kickFreq = 110 * Math.exp(-beatFract * 22);
          kick = Math.sin(2 * Math.PI * kickFreq * t) * Math.exp(-beatFract * 14) * 0.32;
        }
      }

      // Gentle fade in (first 1.5 sec) and fade out (last 2 sec)
      let masterGain = 1.0;
      if (t < 1.5) masterGain = t / 1.5;
      if (t > durationSec - 2.0) masterGain = Math.max(0, (durationSec - t) / 2.0);

      // Combine channels with slight stereo panning for wide studio sound
      const leftMix = (chime * 1.1 + bass * 0.9 + kick * 1.0 + snare * 0.8) * masterGain;
      const rightMix = (chime * 0.9 + bass * 1.1 + kick * 1.0 + snare * 1.1) * masterGain;

      const leftClamped = Math.max(-1, Math.min(1, leftMix));
      const rightClamped = Math.max(-1, Math.min(1, rightMix));

      buffer.writeInt16LE(Math.floor(leftClamped * 32767), offset);
      buffer.writeInt16LE(Math.floor(rightClamped * 32767), offset + 2);
      offset += 4;
    }

    fs.writeFileSync(outputPath, buffer);
    return outputPath;
  }
}

module.exports = new NurserySynthesizer();
