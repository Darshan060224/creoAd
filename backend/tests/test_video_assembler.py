#!/usr/bin/env python3
"""
Comprehensive test suite for modules/video_assembler.py

Covers:
  1. safe_text – character sanitisation, escaping, truncation
  2. build_kinetic_typography – all purpose types (hook, problem, solution, proof, cta, default)
  3. _build_audio_filter – every combination of voice/music/sfx with & without video filters
  4. _resolve_camera_effect / _resolve_transition – mapping correctness
  5. Full end-to-end assemble_video – generates real test images, runs FFmpeg,
     verifies output MP4 is a valid file
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ── path setup ──────────────────────────────────────────────────────────
BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Stub Redis so pipeline.progress doesn't need a real server
_redis_stub = MagicMock()
_redis_mod = MagicMock()
_redis_mod.Redis.from_url.return_value = _redis_stub
sys.modules.setdefault("redis", _redis_mod)

from modules.video_assembler import (
    safe_text,
    build_kinetic_typography,
    _build_audio_filter,
    _resolve_camera_effect,
    _resolve_transition,
    assemble_video,
    CAMERA_EFFECTS,
    TRANSITION_MAP,
    RESOLVED_FONT,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. safe_text
# ═══════════════════════════════════════════════════════════════════════

class TestSafeText:
    """Tests for the safe_text helper."""

    def test_plain_string_passes_through(self):
        assert safe_text("Hello world") == "Hello world"

    def test_truncation(self):
        result = safe_text("A" * 100, max_len=10)
        assert len(result) <= 10

    def test_default_max_len_is_35(self):
        result = safe_text("A" * 50)
        assert len(result) <= 35

    def test_newlines_become_spaces(self):
        assert "\n" not in safe_text("line1\nline2")

    def test_dangerous_chars_stripped(self):
        out = safe_text("a;b&c<d>e|f{g}h(i)j[k]l`m")
        for ch in ";& <>|{}()[]`":
            assert ch not in out

    def test_quotes_replaced(self):
        out = safe_text("it's \"great\"")
        assert "'" not in out
        assert '"' not in out

    def test_ampersand_at_percent(self):
        out = safe_text("A&B@C%D")
        # & is stripped by regex before .replace("&","and") runs, so only @ and % are replaced
        assert "at" in out    # @ → at
        assert "pct" in out   # % → pct
        assert "&" not in out
        assert "@" not in out
        assert "%" not in out

    def test_colons_escaped(self):
        out = safe_text("time: 12:30")
        assert ":" not in out.replace("\\:", "")
        assert "\\:" in out

    def test_backslashes_removed_first(self):
        out = safe_text("path\\to\\file")
        assert "\\" not in out or "\\:" in out  # only escaped colons remain

    def test_empty_string(self):
        assert safe_text("") == ""

    def test_none_returns_empty(self):
        assert safe_text(None) == ""


# ═══════════════════════════════════════════════════════════════════════
# 2. build_kinetic_typography  (the CTA bounce was the crash bug)
# ═══════════════════════════════════════════════════════════════════════

class TestKineticTypography:
    """Validate that every purpose type produces valid FFmpeg drawtext filters."""

    PURPOSES = ["hook", "problem", "solution", "proof", "cta", "default_scene"]

    @staticmethod
    def _make_scenes(purpose: str, text: str = "Buy Now", dur: float = 5.0):
        return [{"purpose": purpose, "text_overlay": text, "duration": dur}]

    def _assert_valid_filter(self, flt: str, label: str):
        """Check the filter string for common FFmpeg-breaking issues."""
        # No un-escaped spaces adjacent to operators inside y= or x= values
        # The old bug: y=h-100 - 15*abs(...)  ← space before minus
        # FFmpeg drawtext params are colon-separated; a bare space inside an
        # expression value doesn't always crash, but a space-dash does in the
        # middle of a key=value when FFmpeg re-parses the filter chain.
        
        # Extract all y=<...> and x=<...> values
        for param in ("x", "y"):
            pattern = rf"{param}=([^:]+)"
            for match in re.finditer(pattern, flt):
                val = match.group(1)
                # Must NOT contain " - " or " + " (space around operators)
                # inside an expression that has parentheses (i.e. is a formula)
                if "(" in val:
                    assert " - " not in val, (
                        f"[{label}] Space around '-' in {param}={val} will break FFmpeg"
                    )
                    assert " + " not in val, (
                        f"[{label}] Space around '+' in {param}={val} will break FFmpeg"
                    )

        # Every drawtext= must have a matching enable= so filters are time-gated
        for dt in flt.split("drawtext="):
            if dt.strip():
                assert "enable=" in dt, f"[{label}] drawtext without enable= found"

    @pytest.mark.parametrize("purpose", PURPOSES)
    def test_purpose_produces_nonempty_filter(self, purpose):
        flt = build_kinetic_typography(
            self._make_scenes(purpose), w=1920, h=1080, font_size=64
        )
        assert len(flt) > 0, f"Empty filter for purpose={purpose}"

    @pytest.mark.parametrize("purpose", PURPOSES)
    def test_purpose_no_space_operators(self, purpose):
        flt = build_kinetic_typography(
            self._make_scenes(purpose), w=1920, h=1080, font_size=64
        )
        self._assert_valid_filter(flt, purpose)

    def test_cta_bounce_no_spaces_in_y(self):
        """Regression test: CTA purpose must not have 'h-100 - 15*abs(...)' with spaces."""
        flt = build_kinetic_typography(
            self._make_scenes("cta", "Shop Now", 5.0), w=1920, h=1080, font_size=64
        )
        # The old crash: "h-100 - 15*abs(sin(5*(t-0.0)))"
        assert "h-100 -" not in flt, "CTA y-expression still has space around minus"
        assert "h-100-15*abs" in flt, "CTA bounce formula missing expected pattern"

    def test_multiple_scenes_concatenated(self):
        scenes = [
            {"purpose": "hook", "text_overlay": "Wow", "duration": 3},
            {"purpose": "problem", "text_overlay": "Issue", "duration": 4},
            {"purpose": "cta", "text_overlay": "Buy", "duration": 3},
        ]
        flt = build_kinetic_typography(scenes, 1920, 1080, 64)
        # Should have 6 drawtext filters (shadow + main for each scene)
        assert flt.count("drawtext=") == 6

    def test_empty_text_skipped(self):
        scenes = [{"purpose": "hook", "text_overlay": "", "duration": 5}]
        flt = build_kinetic_typography(scenes, 1920, 1080, 64)
        assert flt == ""

    def test_zero_duration_skipped(self):
        scenes = [{"purpose": "cta", "text_overlay": "Buy", "duration": 0}]
        flt = build_kinetic_typography(scenes, 1920, 1080, 64)
        assert flt == ""

    def test_shadow_offset_is_parenthesized_for_complex_exprs(self):
        """Shadow pass appends +4 to x/y; complex expressions need parens."""
        flt = build_kinetic_typography(
            self._make_scenes("cta", "Go", 5), 1920, 1080, 64
        )
        # The shadow pass for CTA should have y=(h-100-15*abs(...))+4
        # not y=h-100-15*abs(...)+4
        shadow_parts = flt.split("drawtext=")
        # First drawtext is shadow
        if len(shadow_parts) > 1:
            shadow = shadow_parts[1]
            # Check y param of shadow
            y_match = re.search(r"y=([^:]+)", shadow)
            if y_match:
                y_val = y_match.group(1)
                if "abs" in y_val:
                    assert y_val.startswith("("), (
                        f"Shadow y-expression not parenthesized: {y_val}"
                    )


# ═══════════════════════════════════════════════════════════════════════
# 3. _build_audio_filter  — every combination
# ═══════════════════════════════════════════════════════════════════════

class TestBuildAudioFilter:
    """Test all 8 combinations of voice/music/sfx × with/without video filters."""

    VF = "drawtext=text='test':fontsize=30:fontcolor=white:x=10:y=10:enable='between(t,0,5)'"

    @pytest.mark.parametrize("vf", ["", VF])
    def test_voice_music_sfx(self, vf):
        af, maps = _build_audio_filter(vf, True, True, True, 1, 2, 3, 30)
        assert any("-filter_complex" in a for a in af)
        assert "[a]" in " ".join(maps)

    @pytest.mark.parametrize("vf", ["", VF])
    def test_voice_music_only(self, vf):
        af, maps = _build_audio_filter(vf, True, True, False, 1, 2, None, 30)
        assert any("-filter_complex" in a for a in af)
        fc = af[af.index("-filter_complex") + 1]
        assert "sidechaincompress" in fc

    @pytest.mark.parametrize("vf", ["", VF])
    def test_voice_sfx_only(self, vf):
        af, maps = _build_audio_filter(vf, True, False, True, 1, None, 2, 30)
        assert any("-filter_complex" in a for a in af)

    @pytest.mark.parametrize("vf", ["", VF])
    def test_voice_only(self, vf):
        af, maps = _build_audio_filter(vf, True, False, False, 1, None, None, 30)
        assert "1:a" in " ".join(maps)

    @pytest.mark.parametrize("vf", ["", VF])
    def test_music_sfx_only(self, vf):
        af, maps = _build_audio_filter(vf, False, True, True, None, 1, 2, 30)
        assert any("-filter_complex" in a for a in af)

    @pytest.mark.parametrize("vf", ["", VF])
    def test_music_only(self, vf):
        af, maps = _build_audio_filter(vf, False, True, False, None, 1, None, 30)
        assert "1:a" in " ".join(maps)

    @pytest.mark.parametrize("vf", ["", VF])
    def test_sfx_only(self, vf):
        af, maps = _build_audio_filter(vf, False, False, True, None, None, 1, 30)
        assert "1:a" in " ".join(maps)

    @pytest.mark.parametrize("vf", ["", VF])
    def test_no_audio(self, vf):
        af, maps = _build_audio_filter(vf, False, False, False, None, None, None, 30)
        assert "0:v" in " ".join(maps)

    def test_filter_complex_with_vf_contains_vout(self):
        """When vf_final is non-empty, the filter_complex should pipe video through [vout]."""
        af, maps = _build_audio_filter(self.VF, True, True, True, 1, 2, 3, 30)
        fc = af[af.index("-filter_complex") + 1]
        assert "[vout]" in fc
        assert "[vout]" in " ".join(maps)

    def test_no_filter_complex_without_vf_or_audio(self):
        af, maps = _build_audio_filter("", False, False, False, None, None, None, 30)
        assert "-filter_complex" not in af


# ═══════════════════════════════════════════════════════════════════════
# 4. Camera effects & transitions
# ═══════════════════════════════════════════════════════════════════════

class TestCameraAndTransitions:

    @pytest.mark.parametrize("cam", list(CAMERA_EFFECTS.keys()))
    def test_every_camera_effect_resolves(self, cam):
        result = _resolve_camera_effect(cam, 150)
        assert "zoompan=" in result
        # d= should be substituted, no {d} left
        assert "{d}" not in result

    def test_speed_ramp_substitutes_d_sq(self):
        result = _resolve_camera_effect("speed_ramp_in", 100)
        assert "{d_sq}" not in result

    @pytest.mark.parametrize("trans", list(TRANSITION_MAP.keys()))
    def test_every_transition_maps(self, trans):
        result = _resolve_transition(trans)
        assert result  # non-empty

    def test_unknown_transition_falls_back(self):
        result = _resolve_transition("totally_unknown_effect")
        assert result == "dissolve"

    def test_known_ffmpeg_transition_passes_through(self):
        assert _resolve_transition("smoothleft") == "smoothleft"


# ═══════════════════════════════════════════════════════════════════════
# 5. End-to-end assemble_video (requires FFmpeg)
# ═══════════════════════════════════════════════════════════════════════

def _has_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def _make_test_image(path: str, w: int = 1024, h: int = 576, color: str = "blue"):
    """Create a solid-color test image using FFmpeg (no PIL dependency)."""
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:d=0.04",
        "-frames:v", "1",
        path
    ], capture_output=True, timeout=10)
    assert os.path.exists(path), f"Failed to create test image {path}"


def _make_test_audio(path: str, dur: float = 5.0):
    """Create a short sine-wave WAV using FFmpeg."""
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={dur}",
        "-ar", "44100", "-ac", "2",
        path
    ], capture_output=True, timeout=10)
    assert os.path.exists(path), f"Failed to create test audio {path}"


@pytest.mark.skipif(not _has_ffmpeg(), reason="FFmpeg not installed")
class TestAssembleVideoE2E:
    """Full end-to-end render test.  Creates real images, runs FFmpeg."""

    def _run_assemble(self, tmpdir, structured_scenes, voice=True, music=True,
                      sfx=True, fmt="tv", duration=6):
        """Helper: generate assets and call assemble_video."""
        output_dir = str(tmpdir)

        # Create scene images
        colors = ["red", "green", "blue", "yellow", "purple"]
        for i, scene in enumerate(structured_scenes):
            img_path = os.path.join(output_dir, f"scene_{i:02d}.png")
            _make_test_image(img_path, color=colors[i % len(colors)])
            for shot in scene.get("shots", []):
                shot["image"] = img_path

        # Create audio assets
        voice_path = os.path.join(output_dir, "voice.wav") if voice else None
        music_path = os.path.join(output_dir, "music.wav") if music else None
        sfx_path = os.path.join(output_dir, "sfx.wav") if sfx else None

        if voice_path:
            _make_test_audio(voice_path, dur=duration)
        if music_path:
            _make_test_audio(music_path, dur=duration)
        if sfx_path:
            _make_test_audio(sfx_path, dur=duration)

        script = {"headline": "Test Ad", "cta": "Buy Now!"}

        return assemble_video(
            structured_scenes=structured_scenes,
            voice_path=voice_path,
            music_path=music_path,
            sfx_path=sfx_path,
            script=script,
            job_id="test-001",
            output_dir=output_dir,
            fmt=fmt,
            duration=duration,
        )

    def test_basic_render_with_all_audio(self, tmp_path):
        """Most common case: 3 scenes, voice + music + sfx."""
        scenes = [
            {
                "purpose": "hook",
                "text_overlay": "Amazing Product",
                "duration": 2,
                "transition": "dissolve",
                "shots": [{"camera": "zoom_in", "speed": "medium", "duration": 2}],
            },
            {
                "purpose": "solution",
                "text_overlay": "It Works",
                "duration": 2,
                "transition": "fade",
                "shots": [{"camera": "pan_right", "speed": "medium", "duration": 2}],
            },
            {
                "purpose": "cta",
                "text_overlay": "Buy Now",
                "duration": 2,
                "transition": "dissolve",
                "shots": [{"camera": "push_in", "speed": "medium", "duration": 2}],
            },
        ]
        out = self._run_assemble(tmp_path, scenes, duration=6)
        assert os.path.exists(out), "Output MP4 not created"
        assert os.path.getsize(out) > 1000, "Output file suspiciously small"

    def test_render_voice_only(self, tmp_path):
        """Render with only voice (no music, no SFX)."""
        scenes = [
            {
                "purpose": "hook",
                "text_overlay": "Hello",
                "duration": 3,
                "transition": "fade",
                "shots": [{"camera": "zoom_in", "speed": "medium", "duration": 3}],
            },
        ]
        out = self._run_assemble(tmp_path, scenes, voice=True, music=False, sfx=False, duration=3)
        assert os.path.exists(out)

    def test_render_no_audio(self, tmp_path):
        """Render with zero audio tracks."""
        scenes = [
            {
                "purpose": "solution",
                "text_overlay": "Silent Ad",
                "duration": 3,
                "transition": "fade",
                "shots": [{"camera": "static", "speed": "medium", "duration": 3}],
            },
        ]
        out = self._run_assemble(tmp_path, scenes, voice=False, music=False, sfx=False, duration=3)
        assert os.path.exists(out)

    def test_all_purposes_in_one_ad(self, tmp_path):
        """Regression: render an ad that uses every scene purpose (including CTA bounce)."""
        scenes = [
            {
                "purpose": "hook",
                "text_overlay": "Attention",
                "duration": 2,
                "transition": "fade",
                "shots": [{"camera": "crash_zoom_in", "speed": "fast", "duration": 2}],
            },
            {
                "purpose": "problem",
                "text_overlay": "The Problem",
                "duration": 2,
                "transition": "slideleft",
                "shots": [{"camera": "push_in", "speed": "medium", "duration": 2}],
            },
            {
                "purpose": "solution",
                "text_overlay": "Our Fix",
                "duration": 2,
                "transition": "dissolve",
                "shots": [{"camera": "parallax", "speed": "slow", "duration": 2}],
            },
            {
                "purpose": "proof",
                "text_overlay": "5 Stars",
                "duration": 2,
                "transition": "smoothleft",
                "shots": [{"camera": "orbit_left", "speed": "medium", "duration": 2}],
            },
            {
                "purpose": "cta",
                "text_overlay": "Get It Now",
                "duration": 2,
                "transition": "dissolve",
                "shots": [{"camera": "push_in", "speed": "medium", "duration": 2}],
            },
        ]
        out = self._run_assemble(tmp_path, scenes, duration=10)
        assert os.path.exists(out), "Full-purpose render failed"
        assert os.path.getsize(out) > 5000

    def test_mobile_format(self, tmp_path):
        """Render in 1080×1920 mobile portrait format."""
        scenes = [
            {
                "purpose": "hook",
                "text_overlay": "Mobile Ad",
                "duration": 3,
                "transition": "fade",
                "shots": [{"camera": "zoom_in", "speed": "medium", "duration": 3}],
            },
        ]
        out = self._run_assemble(tmp_path, scenes, fmt="mobile", duration=3)
        assert os.path.exists(out)

    def test_square_format(self, tmp_path):
        """Render in 1080×1080 square format."""
        scenes = [
            {
                "purpose": "hook",
                "text_overlay": "Square Ad",
                "duration": 3,
                "transition": "fade",
                "shots": [{"camera": "zoom_in", "speed": "medium", "duration": 3}],
            },
        ]
        out = self._run_assemble(tmp_path, scenes, fmt="square", duration=3)
        assert os.path.exists(out)

    def test_special_chars_in_text(self, tmp_path):
        """Text with colons, quotes, ampersands should not crash FFmpeg."""
        scenes = [
            {
                "purpose": "cta",
                "text_overlay": "Sale: 50% off & more! It's great",
                "duration": 3,
                "transition": "fade",
                "shots": [{"camera": "push_in", "speed": "medium", "duration": 3}],
            },
        ]
        out = self._run_assemble(tmp_path, scenes, voice=False, music=False, sfx=False, duration=3)
        assert os.path.exists(out)

    def test_image_paths_fallback(self, tmp_path):
        """When structured_scenes is None, image_paths list should work."""
        output_dir = str(tmp_path)
        imgs = []
        for i in range(3):
            p = os.path.join(output_dir, f"img_{i}.png")
            _make_test_image(p, color=["red", "green", "blue"][i])
            imgs.append(p)

        out = assemble_video(
            structured_scenes=None,
            voice_path=None,
            music_path=None,
            sfx_path=None,
            script={"headline": "Fallback", "cta": "Go"},
            job_id="test-fallback",
            output_dir=output_dir,
            fmt="tv",
            duration=6,
            image_paths=imgs,
        )
        assert os.path.exists(out)
