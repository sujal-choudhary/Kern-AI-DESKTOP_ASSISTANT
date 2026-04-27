import io
import logging
import os
import tempfile
import wave

from piper import PiperVoice
import winsound

from config import VOICE_MODEL_PATH

voice = None

def speak(text):
    """Convert text to speech using Piper TTS"""
    global voice
    try:
        if voice is None:
            voice = PiperVoice.load(VOICE_MODEL_PATH)
        wav_bytes = io.BytesIO()
        with wave.open(wav_bytes, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        wav_bytes.seek(0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(wav_bytes.read())
            tmp_path = tmp.name
        try:
            if os.name == "nt":
                winsound.PlaySound(tmp_path, winsound.SND_FILENAME)
            else:
                print(text)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        logging.info(f"Spoke: {text}")
    except Exception as exc:
        logging.error("Error in TTS: %s", exc)
        print(text)