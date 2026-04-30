"""
Generates a voiceover from a script using Google AI Studio (Gemini TTS).
Saves output as MP3 via ffmpeg (bundled with moviepy/imageio_ffmpeg).

Available Gemini voices: Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede
"""
import struct
import subprocess
import time
import wave
from pathlib import Path

from google import genai
from google.genai import types
from imageio_ffmpeg import get_ffmpeg_exe

from config import GOOGLE_AI_STUDIO_API_KEY, GEMINI_TTS_VOICE
from utils.logger import get_logger

log = get_logger(__name__)

# Gemini TTS returns 24kHz mono 16-bit PCM
SAMPLE_RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit


def _pcm_to_wav(pcm_data: bytes, wav_path: Path):
    """Wrap raw PCM bytes in a proper WAV container."""
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)


def _wav_to_mp3(wav_path: Path, mp3_path: Path):
    """Convert WAV to MP3 using the ffmpeg bundled with imageio_ffmpeg."""
    ffmpeg = get_ffmpeg_exe()
    result = subprocess.run(
        [ffmpeg, "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-qscale:a", "2", str(mp3_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr[-300:]}")


def generate_voiceover(script: str, output_path: Path, retries: int = 3) -> Path:
    """
    Send *script* to Gemini TTS and save the result as MP3 at *output_path*.
    Returns *output_path* on success.
    """
    client = genai.Client(api_key=GOOGLE_AI_STUDIO_API_KEY)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path = output_path.with_suffix(".wav")

    for attempt in range(1, retries + 1):
        try:
            log.info("Generating voiceover with Gemini TTS (attempt %d)…", attempt)

            response = client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=script,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=GEMINI_TTS_VOICE
                            )
                        )
                    ),
                ),
            )

            # Extract raw PCM audio from response
            audio_part = response.candidates[0].content.parts[0].inline_data
            pcm_data = audio_part.data  # already bytes in the new SDK

            # Save as WAV then convert to MP3
            _pcm_to_wav(pcm_data, wav_path)
            _wav_to_mp3(wav_path, output_path)
            wav_path.unlink(missing_ok=True)  # clean up temp WAV

            size_kb = output_path.stat().st_size // 1024
            log.info("Voiceover saved -> %s (%d KB)", output_path, size_kb)
            return output_path

        except Exception as exc:
            log.warning("Voiceover attempt %d failed: %s", attempt, exc)
            if attempt < retries:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"Voiceover generation failed after {retries} attempts")
