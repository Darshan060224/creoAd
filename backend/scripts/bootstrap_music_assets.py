"""
Create starter local royalty-free background tracks under backend/assets/music.

Usage:
  python backend/scripts/bootstrap_music_assets.py
"""

from __future__ import annotations

from pathlib import Path

from pydub import AudioSegment
from pydub.generators import Sine


def build_track(freq: int, duration_ms: int = 30000) -> AudioSegment:
    """Generate a simple low-volume tone bed."""
    tone = Sine(freq).to_audio_segment(duration=duration_ms)
    return tone - 28


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    music_dir = root / "assets" / "music"
    music_dir.mkdir(parents=True, exist_ok=True)

    tracks = {
        "upbeat_loop.mp3": 330,
        "professional_loop.mp3": 262,
        "calm_loop.mp3": 220,
    }

    for filename, freq in tracks.items():
        out_path = music_dir / filename
        if out_path.exists():
            continue
        build_track(freq).export(out_path, format="mp3")
        print(f"Created {out_path}")

    print("Music bootstrap complete.")


if __name__ == "__main__":
    main()
