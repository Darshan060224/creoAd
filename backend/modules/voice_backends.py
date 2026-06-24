"""
Local voice backend helpers for CreoAd.
Supports Chatterbox first, then Coqui TTS, then pyttsx3, then espeak-ng fallback.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional


# Pace mapping: words per minute
PACE_MAP = {
    "slow": 120,
    "medium": 150,
    "fast": 180,
    "very_fast": 210,
}


def _run_command(command: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout)


def _resolve_chatterbox_device() -> str:
    configured_device = os.getenv("CHATTERBOX_DEVICE", "").strip().lower()
    if configured_device in {"cpu", "cuda"}:
        return configured_device

    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass

    return "cpu"


def is_command_available(command_name: str) -> bool:
    return subprocess.run(["which", command_name], capture_output=True).returncode == 0


def generate_chatterbox_voiceover(text: str, output_path: str, audio_prompt_path: Optional[str] = None) -> str:
    """Generate voice using the local Chatterbox package if available."""

    try:
        import torchaudio as ta
        try:
            from chatterbox.tts_turbo import ChatterboxTurboTTS
            turbo_available = True
        except Exception:
            from chatterbox.tts import ChatterboxTTS
            turbo_available = False
    except Exception as exc:
        raise RuntimeError(f"Chatterbox is not available: {exc}")

    device = _resolve_chatterbox_device()

    if turbo_available:
        model = ChatterboxTurboTTS.from_pretrained(device=device)
        wav = model.generate(text, audio_prompt_path=audio_prompt_path)
    else:
        model = ChatterboxTTS.from_pretrained(device=device)
        wav = model.generate(text, audio_prompt_path=audio_prompt_path)

    ta.save(output_path, wav, model.sr)
    return output_path


def generate_coqui_voiceover(text: str, output_path: str, model_name: Optional[str] = None) -> str:
    """Generate voice using the Coqui TTS CLI if installed."""

    selected_model = model_name or os.getenv("COQUI_TTS_MODEL", "tts_models/en/ljspeech/tacotron2-DDC")
    command = [
        "tts",
        "--text", text,
        "--model_name", selected_model,
        "--out_path", output_path,
        "--progress_bar", "False",
    ]

    use_gpu = os.getenv("COQUI_TTS_GPU", "false").lower() in {"1", "true", "yes"}
    if use_gpu:
        command.append("--gpu")

    try:
        from config import settings
        timeout_val = settings.ollama_request_timeout
    except ImportError:
        timeout_val = 300

    result = _run_command(command, timeout=timeout_val)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Coqui TTS failed")

    if not Path(output_path).exists():
        raise RuntimeError(f"Output file not created: {output_path}")

    return output_path


def generate_pyttsx3_voiceover(text: str, output_path: str, rate: int = 150, pace: str = "medium") -> str:
    """Offline fallback voice generation with pyttsx3."""

    import pyttsx3

    # Map pace to words per minute
    wpm = PACE_MAP.get(pace, rate)

    engine = pyttsx3.init()
    engine.setProperty("rate", wpm)
    engine.setProperty("volume", 1.0)
    engine.save_to_file(text, output_path)
    engine.runAndWait()
    return output_path


def generate_espeak_voiceover(text: str, output_path: str, pace: str = "medium") -> str:
    """Fallback voice generation using espeak-ng (available on most Linux systems)."""

    speed_map = {"slow": "120", "medium": "160", "fast": "200", "very_fast": "240"}
    speed = speed_map.get(pace, "160")

    # Try espeak-ng first, then espeak
    for cmd_name in ["espeak-ng", "espeak"]:
        if is_command_available(cmd_name):
            command = [
                cmd_name,
                "-w", output_path,
                "-s", speed,
                "-v", "en",
                text,
            ]
            result = _run_command(command, timeout=30)
            if result.returncode == 0 and Path(output_path).exists():
                return output_path

    raise RuntimeError("Neither espeak-ng nor espeak is available")


def create_silent_audio(output_path: str, duration: int = 7) -> str:
    """Create a silent WAV fallback if every speech engine fails."""

    import struct
    import wave

    sample_rate = 44100
    num_channels = 2
    sample_width = 2

    with wave.open(output_path, "wb") as wav_file:
        wav_file.setnchannels(num_channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        num_frames = int(sample_rate * duration)
        silence = struct.pack("<h", 0) * num_frames * num_channels
        wav_file.writeframes(silence)

    return output_path
