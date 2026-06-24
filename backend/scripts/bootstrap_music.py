#!/usr/bin/env python3
"""
One-time bootstrap script to download royalty-free music tracks for CreoAd.
Run this once to populate backend/assets/music/ with tracks.

Usage:
    python -m backend.scripts.bootstrap_music
    # or
    python backend/scripts/bootstrap_music.py
"""

import os
import sys
import urllib.request
from pathlib import Path


# Royalty-free tracks from Pixabay (Creative Commons)
TRACKS = {
    "upbeat_corporate.mp3": "https://cdn.pixabay.com/audio/2022/05/27/audio_1808fbf07a.mp3",
    "calm_ambient.mp3": "https://cdn.pixabay.com/audio/2022/10/25/audio_946bc34898.mp3",
    "dramatic_cinematic.mp3": "https://cdn.pixabay.com/audio/2022/02/22/audio_d1718ab41b.mp3",
    "energetic_electronic.mp3": "https://cdn.pixabay.com/audio/2022/03/10/audio_d65611036b.mp3",
    "warm_acoustic.mp3": "https://cdn.pixabay.com/audio/2022/08/23/audio_ea95765a43.mp3",
}


def bootstrap_music(music_dir: str = None):
    """Download royalty-free tracks to the music directory."""
    if music_dir is None:
        # Resolve relative to this script
        script_dir = Path(__file__).resolve().parent.parent
        music_dir = script_dir / "assets" / "music"
    else:
        music_dir = Path(music_dir)

    music_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 Music directory: {music_dir}")
    print(f"📥 Downloading {len(TRACKS)} tracks...\n")

    downloaded = 0
    for filename, url in TRACKS.items():
        output_path = music_dir / filename
        if output_path.exists():
            size_kb = output_path.stat().st_size // 1024
            print(f"  ✓ {filename} already exists ({size_kb}KB)")
            downloaded += 1
            continue

        print(f"  ⬇ Downloading {filename}...", end=" ", flush=True)
        try:
            urllib.request.urlretrieve(url, output_path)
            size_kb = output_path.stat().st_size // 1024
            print(f"✓ ({size_kb}KB)")
            downloaded += 1
        except Exception as e:
            print(f"✗ Failed: {e}")

    print(f"\n{'='*50}")
    print(f"✅ {downloaded}/{len(TRACKS)} tracks ready in {music_dir}")
    if downloaded < len(TRACKS):
        print("⚠  Some downloads failed. You can manually place .mp3 files in the music directory.")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    bootstrap_music(target)
