from __future__ import annotations

import platform
import subprocess
import tempfile
from pathlib import Path

import numpy as np

_WHISPER = None
_SAMPLE_RATE = 16000


def voice_available() -> bool:
    try:
        import sounddevice  # noqa: F401
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return platform.system() == "Darwin"


def _load_whisper(model_name: str):
    global _WHISPER
    if _WHISPER is None:
        from faster_whisper import WhisperModel

        _WHISPER = WhisperModel(model_name, device="cpu", compute_type="int8")
    return _WHISPER


def record_seconds(seconds: int) -> np.ndarray:
    import sounddevice as sd

    frames = int(seconds * _SAMPLE_RATE)
    print(f"Listening for {seconds}s...")
    audio = sd.rec(frames, samplerate=_SAMPLE_RATE, channels=1, dtype="float32")
    sd.wait()
    return audio.flatten()


def transcribe(audio: np.ndarray, model_name: str) -> str:
    if audio.size == 0:
        return ""
    model = _load_whisper(model_name)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)
    try:
        import soundfile as sf

        sf.write(str(wav_path), audio, _SAMPLE_RATE)
        segments, _ = model.transcribe(str(wav_path), beam_size=1, language="en")
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text
    finally:
        wav_path.unlink(missing_ok=True)


def listen_once(model_name: str, seconds: int) -> str:
    if not voice_available():
        raise RuntimeError(
            "Voice requires macOS plus: pip install faster-whisper sounddevice soundfile"
        )
    audio = record_seconds(seconds)
    text = transcribe(audio, model_name=model_name)
    return text


def speak(text: str) -> None:
    if platform.system() != "Darwin":
        return
    clean = " ".join(text.split())
    if not clean:
        return
    # Keep speech short and skip source listing noise.
    if "Sources:" in clean:
        clean = clean.split("Sources:")[0].strip()
    clean = clean[:500]
    subprocess.run(["say", clean], check=False)
