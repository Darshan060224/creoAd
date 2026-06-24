"""
Stage B5: Synthetic Sound Effects Generator.
Generates SFX using FFmpeg audio synthesis — no external files needed.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional


# FFmpeg lavfi audio synthesis expressions for each effect type
SFX_GENERATORS = {
    "impact": "sine=f=80:d=0.15,afade=t=out:d=0.1",
    "whoosh": "anoisesrc=d=0.4,bandpass=f=2000:w=1000,afade=t=in:d=0.1,afade=t=out:st=0.2:d=0.2",
    "riser": "sine=f=200:d=1.5,asetrate=44100*1.5,afade=t=in:d=0.3",
    "click": "sine=f=4000:d=0.05,afade=t=out:d=0.03",
    "boom": "sine=f=40:d=0.5,afade=t=out:d=0.3",
    "pop": "sine=f=1500:d=0.08,afade=t=out:d=0.05",
    "hit": "sine=f=100:d=0.2,afade=t=out:d=0.15",
    "swipe": "anoisesrc=d=0.3,bandpass=f=3000:w=2000,afade=t=in:d=0.05,afade=t=out:d=0.2",
    "sweep": "sine=f=300:d=0.8,asetrate=44100*2.0,afade=t=in:d=0.1,afade=t=out:st=0.5:d=0.3",
    "ding": "sine=f=2000:d=0.3,afade=t=out:d=0.25",
}

# Duration in seconds for each effect type
SFX_DURATIONS = {
    "impact": 0.15,
    "whoosh": 0.4,
    "riser": 1.5,
    "click": 0.05,
    "boom": 0.5,
    "pop": 0.08,
    "hit": 0.2,
    "swipe": 0.3,
    "sweep": 0.8,
    "ding": 0.3,
}


def generate_sfx(effect_name: str, output_path: str) -> str:
    """Generate a single synthetic sound effect WAV file.
    
    Args:
        effect_name: Name of the effect (must be a key in SFX_GENERATORS)
        output_path: Where to save the WAV file
        
    Returns:
        Path to generated WAV file
    """
    generator = SFX_GENERATORS.get(effect_name.lower(), SFX_GENERATORS["impact"])
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", generator,
        "-ar", "44100",
        "-ac", "2",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, timeout=10)
    if result.returncode != 0:
        raise RuntimeError(f"SFX generation failed for '{effect_name}': {result.stderr.decode()[:200]}")
    
    return output_path


def generate_sfx_track(
    timeline: List[Dict], total_duration: float, output_path: str
) -> str:
    """Composite all SFX into one audio track at correct timestamps.
    
    Args:
        timeline: List of {"time": float, "effect": str} events
        total_duration: Total video duration in seconds
        output_path: Where to save the final composite WAV
        
    Returns:
        Path to the composite SFX track
    """
    if not timeline:
        # Return empty/silent track
        _generate_silent(output_path, total_duration)
        return output_path
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Generate individual SFX files
    sfx_files = []
    valid_events = []
    
    for i, event in enumerate(timeline):
        if not isinstance(event, dict):
            continue
        effect = event.get("effect", "impact")
        t = float(event.get("time", 0))
        
        if t < 0 or t >= total_duration:
            continue
        
        sfx_path = output_path + f".sfx_{i:02d}.wav"
        try:
            generate_sfx(effect, sfx_path)
            sfx_files.append(sfx_path)
            valid_events.append(event)
        except Exception as e:
            print(f"SFX generation failed for event {i} ({effect}): {e}")
            continue
    
    if not sfx_files:
        _generate_silent(output_path, total_duration)
        return output_path
    
    # Build FFmpeg command to mix all SFX at their timestamps on a silent base
    # Strategy: create a silent base track, then overlay each SFX at its timestamp
    
    # First create base silent track
    base_path = output_path + ".base.wav"
    _generate_silent(base_path, total_duration)
    
    # Use FFmpeg's adelay and amix to composite
    inputs = ["-i", base_path]
    for sfx in sfx_files:
        inputs += ["-i", sfx]
    
    # Build the filter: delay each SFX input, then mix all together
    filter_parts = []
    n = len(sfx_files)
    
    for i, event in enumerate(valid_events):
        delay_ms = int(float(event.get("time", 0)) * 1000)
        # Input index is i+1 (since input 0 is the base silent track)
        filter_parts.append(f"[{i+1}:a]adelay={delay_ms}|{delay_ms},volume=0.7[sfx{i}]")
    
    # Mix everything together
    mix_inputs = "[0:a]" + "".join(f"[sfx{i}]" for i in range(n))
    filter_parts.append(f"{mix_inputs}amix=inputs={n+1}:duration=first:dropout_transition=0[out]")
    
    filter_complex = ";".join(filter_parts)
    
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-ar", "44100",
        "-ac", "2",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    
    # Cleanup temp files
    _cleanup_temp_files(base_path, sfx_files)
    
    if result.returncode != 0:
        # Fallback: return silence instead of failing
        print(f"SFX track compositing failed: {result.stderr.decode()[:200]}")
        _generate_silent(output_path, total_duration)
    
    return output_path


def _generate_silent(output_path: str, duration: float) -> str:
    """Generate a silent audio track."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(duration),
        output_path
    ]
    subprocess.run(cmd, capture_output=True, timeout=10)
    return output_path


def _cleanup_temp_files(base_path: str, sfx_files: List[str]) -> None:
    """Remove temporary SFX files."""
    for f in [base_path] + sfx_files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass
