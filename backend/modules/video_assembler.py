import subprocess
import os
import time

try:
    from ..config import settings
    from ..pipeline.progress import pub_start, pub_log, pub_done
except ImportError:
    from config import settings
    from pipeline.progress import pub_start, pub_log, pub_done

VIDEO_SPECS = {
    "tv":     {"w": 1920, "h": 1080, "vb": "5000k", "ab": "192k", "ar": 48000},
    "laptop": {"w": 1280, "h": 720,  "vb": "2500k", "ab": "128k", "ar": 44100},
    "mobile": {"w": 1080, "h": 1920, "vb": "3000k", "ab": "128k", "ar": 44100},
    "square": {"w": 1080, "h": 1080, "vb": "3000k", "ab": "128k", "ar": 44100},
}

CAMERA_EFFECTS = {
    "zoom_in": "zoompan=z='min(zoom+0.0008,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}",
    "zoom_out": "zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0008))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}",
    "pan_right": "zoompan=z='1.3':x='if(gte(on,1),x+1,0)':y='ih/2-(ih/zoom/2)':d={d}",
    "pan_left": "zoompan=z='1.3':x='if(gte(on,1),max(0,x-1),iw)':y='ih/2-(ih/zoom/2)':d={d}",
    "pan_up": "zoompan=z='1.3':x='iw/2-(iw/zoom/2)':y='if(gte(on,1),max(0,y-1),ih)':d={d}",
    "pan_down": "zoompan=z='1.3':x='iw/2-(iw/zoom/2)':y='if(gte(on,1),y+1,0)':d={d}",
    "push_in": "zoompan=z='min(zoom+0.001,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}",
    "pull_out": "zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.001))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}",
    "orbit_left": "zoompan=z='1.2':x='if(gte(on,1),max(0,x-0.5),iw)':y='ih/2-(ih/zoom/2)':d={d}",
    "orbit_right": "zoompan=z='1.2':x='if(gte(on,1),x+0.5,0)':y='ih/2-(ih/zoom/2)':d={d}",
    "parallax": "zoompan=z='min(zoom+0.0005,1.1)':x='if(gte(on,1),x+0.5,0)':y='ih/2-(ih/zoom/2)':d={d}",
    "dolly_in": "zoompan=z='min(zoom+0.001,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}",
    "drone": "zoompan=z='min(zoom+0.0005,1.2)':x='if(gte(on,1),x+0.5,0)':y='if(gte(on,1),y+0.5,0)':d={d}",
    "whip_pan_left": "zoompan=z='1.1':x='if(gte(on,1),max(0,x-3),iw)':y='ih/2-(ih/zoom/2)':d={d}",
    "whip_pan_right": "zoompan=z='1.1':x='if(gte(on,1),x+3,0)':y='ih/2-(ih/zoom/2)':d={d}",
    "crash_zoom_in": "zoompan=z='min(zoom+0.02,2.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}",
    "crash_zoom_out": "zoompan=z='if(lte(zoom,1.0),2.0,max(1.001,zoom-0.02))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}",
    # New Phase 4 camera effects
    "speed_ramp_in": "zoompan=z='min(zoom+0.0003*(on*on/{d_sq}),1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}",
    "speed_ramp_out": "zoompan=z='min(zoom+0.003*(1-on*on/{d_sq}),1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}",
    "drift": "zoompan=z='1.1':x='iw/2-(iw/zoom/2)+10*sin(on*0.02)':y='ih/2-(ih/zoom/2)+5*sin(on*0.03)':d={d}",
    "truck_left": "zoompan=z='1.15':x='if(gte(on,1),max(0,x-0.8),iw/4)':y='ih/2-(ih/zoom/2)':d={d}",
    "truck_right": "zoompan=z='1.15':x='if(gte(on,1),min(iw,x+0.8),0)':y='ih/2-(ih/zoom/2)':d={d}",
    "none": "zoompan=z='1.0':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}",
    "static": "zoompan=z='1.0':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}"
}

# Motion Director transition → FFmpeg xfade transition mapping
TRANSITION_MAP = {
    "cut": "fade",
    "dissolve": "dissolve",
    "whip_pan": "slideleft",
    "match_cut": "smoothleft",
    "flash": "fade",
    "speed_ramp": "zoomin",
    "blur_transition": "smoothup",
    "wipe": "wipeleft",
    "slide": "slideleft",
    "fade": "fade",
    "zoom": "zoomin",
}

# Scene purpose → preferred camera effect and speed
PURPOSE_CAMERA_MAP = {
    "hook": {"camera": "crash_zoom_in", "speed_mult": 2.0},
    "problem": {"camera": "push_in", "speed_mult": 1.0},
    "solution": {"camera": "parallax", "speed_mult": 0.5},
    "proof": {"camera": "orbit_left", "speed_mult": 0.8},
    "cta": {"camera": "push_in", "speed_mult": 1.0},
}

# Speed name → rate multiplier for zoompan
SPEED_MULTIPLIERS = {
    "slow": 0.5,
    "medium": 1.0,
    "fast": 2.0,
    "ramp_up": 1.5,
    "ramp_down": 0.7,
}

DEFAULT_CAMERA = "zoom_in"
DEFAULT_TRANSITION = "dissolve"

# QUAL-C: Font detection for kinetic typography
_FONT_SEARCH_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arial.ttf",
]

def _detect_font() -> str:
    """Find the best available system font for drawtext. Returns fontfile arg or empty string."""
    for path in _FONT_SEARCH_PATHS:
        if os.path.exists(path):
            return f"fontfile='{path}':"
    return ""

RESOLVED_FONT = _detect_font()

def safe_text(text: str, max_len: int = 35) -> str:
    """
    Remove every character that can break FFmpeg's drawtext filter parser.
    Must be called on EVERY string passed into any drawtext= filter.
    """
    import re
    if not text:
        return ""
    text = str(text).replace("\n", " ")
    # 1. Remove ALL quote variants (single, double, smart, backtick)
    text = re.sub(r"""['\"``\u2018\u2019\u201C\u201D]""", "", text)
    # 2. Remove shell/filter-breaking characters
    text = re.sub(r"[;,&<>|\\{}()\[\]=\$]", "", text)
    # 3. Replace special symbols with words
    text = text.replace("@", "at").replace("%", "pct")
    # 4. Escape colons (FFmpeg drawtext key=value separator) LAST
    text = text.replace(":", "\\:")
    # 5. Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)
    return text[:max_len].strip()


def _resolve_camera_effect(camera_type: str, frames: int) -> str:
    """Resolve camera effect string, handling d_sq parameter for speed ramp effects."""
    effect_template = CAMERA_EFFECTS.get(camera_type, CAMERA_EFFECTS[DEFAULT_CAMERA])
    d_sq = max(1, frames * frames)
    return effect_template.format(d=frames, d_sq=d_sq)


def _resolve_transition(transition_name: str) -> str:
    """Map Motion Director transition names to FFmpeg xfade transition names."""
    return TRANSITION_MAP.get(transition_name, transition_name if transition_name in
        ["fade", "dissolve", "wipeleft", "slideleft", "smoothleft", "smoothup", "zoomin"]
        else "dissolve")


def assemble_video(structured_scenes=None, voice_path=None, music_path=None,
                   sfx_path=None, script=None, job_id="unknown", output_dir=".",
                   fmt="tv", duration=30, image_paths=None):

    pub_start(job_id, "render",
        f"FFmpeg · Ken Burns + crossfade · {fmt} · {settings.ffmpeg_preset}")
    start = time.time()

    spec     = VIDEO_SPECS.get(fmt, VIDEO_SPECS["tv"])
    w, h     = spec["w"], spec["h"]
    out_path = os.path.join(output_dir, f"creoad_ad_{fmt}.mp4")
    fps      = 30

    if not image_paths and structured_scenes:
        # Extract image paths and their intended durations from the shots
        image_data = []
        for scene in structured_scenes:
            scene_transition = scene.get("transition", DEFAULT_TRANSITION)
            scene_purpose = scene.get("purpose", "scene")
            for shot in scene.get("shots", []):
                if shot.get("image"):
                    camera = shot.get("camera", DEFAULT_CAMERA)
                    speed = shot.get("speed", "medium")

                    # Apply scene-aware speed variation if no explicit camera assigned
                    if camera == DEFAULT_CAMERA and scene_purpose in PURPOSE_CAMERA_MAP:
                        camera = PURPOSE_CAMERA_MAP[scene_purpose]["camera"]

                    image_data.append({
                        "path": shot.get("image"),
                        "duration": shot.get("duration", duration / max(1, len(structured_scenes))),
                        "camera": camera,
                        "transition": _resolve_transition(scene_transition),
                        "speed": speed,
                        "purpose": scene_purpose,
                    })
    else:
        # Fallback to evenly divided duration if no structured scenes
        n_scenes = len(image_paths) if image_paths else 0
        if n_scenes == 0:
            raise RuntimeError("No images provided")
        avg_dur = duration / n_scenes
        image_data = [{"path": p, "duration": avg_dur, "camera": DEFAULT_CAMERA, "transition": DEFAULT_TRANSITION, "speed": "medium", "purpose": "scene"} for p in image_paths]

    n_scenes = len(image_data)
    if n_scenes == 0:
        raise RuntimeError("No images provided")

    pub_log(job_id, "render",
        f"FFMPEG {n_scenes} shots dynamically timed · "
        f"{w}x{h} · Ken Burns animation", pct=5)

    clip_paths = []
    clip_durations = []
    transitions_list = []
    for i, data in enumerate(image_data):
        img_path = data["path"]
        shot_dur = float(data["duration"])
        camera_type = data.get("camera", DEFAULT_CAMERA)
        transitions_list.append(data.get("transition", DEFAULT_TRANSITION))
        
        clip_durations.append(shot_dur)
        frames = int(shot_dur * fps)
        
        clip_path = os.path.join(output_dir, f"clip_{i:02d}.mp4")
        
        kb = _resolve_camera_effect(camera_type, frames)
        kb += f":s={w}x{h}:fps={fps}"

        fade = f"fade=t=in:st=0:d=0.3,fade=t=out:st={shot_dur-0.3}:d=0.3"
        vf = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
            f"{kb},{fade},format=yuv420p"
        )

        # Attempt true AI Video generation (Wan2.1 / LTX)
        ai_video_path = None
        try:
            from .video_generator import generate_video_clip
            ai_video_path = generate_video_clip(img_path, camera_type, shot_dur, i, output_dir, job_id)
        except ImportError:
            pass
        except Exception as e:
            if os.getenv("REQUIRE_AI_VIDEO", "false").lower() == "true":
                pub_log(job_id, "render", f"VideoGen ✗ AI Video failed: {e}")
                raise RuntimeError(f"AI Video Generation is strictly required but failed: {e}")
            else:
                pub_log(job_id, "render", f"VideoGen ⚠ AI Video failed, using Ken Burns fallback: {e}")
            
        if ai_video_path and os.path.exists(ai_video_path):
            clip_paths.append(ai_video_path)
            pct = 10 + int((i + 1) / n_scenes * 50)
            pub_log(job_id, "render",
                f"VideoGen ✓ Shot {i+1}/{n_scenes} generated via Wan2.1/LTX · {os.path.basename(ai_video_path)}",
                pct=pct)
            continue

        # Fallback to FFmpeg Ken Burns
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-t", str(shot_dur + 0.6),
            "-i", img_path,
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", settings.ffmpeg_preset,
            "-r", str(fps),
            "-t", str(shot_dur + 0.6),
            "-an",
            clip_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=900)

        if result.returncode == 0 and os.path.exists(clip_path):
            clip_paths.append(clip_path)
            pct = 10 + int((i + 1) / n_scenes * 50)
            pub_log(job_id, "render",
                f"VideoGen ✓ Shot {i+1}/{n_scenes} generated via Ken Burns fallback · {os.path.basename(clip_path)}",
                pct=pct)
        else:
            pub_log(job_id, "render",
                f"VideoGen Shot {i+1} generation failed · using static fallback")
            fallback_clip = _static_clip(img_path, shot_dur, w, h, output_dir, i)
            clip_paths.append(fallback_clip)

    if not clip_paths:
        raise RuntimeError("No scene clips generated")

    pub_log(job_id, "render",
        f"FFMPEG Joining {len(clip_paths)} clips with crossfade transitions", pct=65)

    if len(clip_paths) == 1:
        joined = clip_paths[0]
    else:
        joined = _xfade_join(clip_paths, output_dir, clip_durations, transitions_list)

    pub_log(job_id, "render", "FFMPEG Adding audio + text overlays", pct=78)

    # Kinetic Typography (Phase 5 Enhanced)
    headline = safe_text(script.get("headline", ""), 35) if script else ""
    cta      = safe_text(script.get("cta", ""), 30) if script else ""
    vf_final = ""
    font_h = 64 if fmt == "tv" else 44
    font_c = 42 if fmt == "tv" else 28

    if structured_scenes:
        vf_final = build_kinetic_typography(structured_scenes, w, h, font_h)
    else:
        # Fallback to old headline/cta if no structured scenes
        if headline:
            vf_final += f"drawtext=text='{headline}':fontsize={font_h}:fontcolor=white:shadowcolor=0x00000099:shadowx=3:shadowy=3:x=(w-text_w)/2:y=60:enable='between(t,0.5,{duration-4})'"
        if cta:
            sep = "," if vf_final else ""
            vf_final += sep + f"drawtext=text='{cta}':fontsize={font_c}:fontcolor=0xFFD700:shadowcolor=0x00000099:shadowx=3:shadowy=3:x=(w-text_w)/2:y=h-80:enable='between(t,{duration-7},{duration})'"

    # Audio inputs
    has_voice = bool(voice_path and os.path.exists(voice_path) and
                     os.path.getsize(voice_path) > 1000)
    has_music = bool(music_path and os.path.exists(music_path) and
                     os.path.getsize(music_path) > 1000)
    has_sfx = bool(sfx_path and os.path.exists(sfx_path) and
                   os.path.getsize(sfx_path) > 1000)

    inputs = ["-i", joined]
    audio_input_idx = 1
    voice_idx = music_idx = sfx_idx = None

    if has_voice:
        inputs += ["-i", voice_path]
        voice_idx = audio_input_idx
        audio_input_idx += 1
    if has_music:
        inputs += ["-i", music_path]
        music_idx = audio_input_idx
        audio_input_idx += 1
    if has_sfx:
        inputs += ["-i", sfx_path]
        sfx_idx = audio_input_idx
        audio_input_idx += 1

    # Build audio filter complex
    af, maps = _build_audio_filter(
        vf_final, has_voice, has_music, has_sfx,
        voice_idx, music_idx, sfx_idx, duration
    )

    cmd_final = [
        "ffmpeg", "-y",
        "-v", "warning",
        *inputs,
        *af,
        *maps,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high" if fmt == "tv" else "main",
        "-preset", settings.ffmpeg_preset,
        "-b:v", spec["vb"],
        "-r", str(fps),
        "-t", str(duration),
        "-c:a", "aac",
        "-b:a", spec["ab"],
        "-ar", str(spec["ar"]),
        "-ac", "2",
        "-movflags", "+faststart",
        "-progress", "pipe:1",
        out_path
    ]

    proc = subprocess.Popen(cmd_final, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in proc.stdout:
        if b"out_time_ms" in line:
            try:
                ms  = int(line.decode().split("=")[1])
                pct = min(78 + int(ms / (duration * 1000000) * 20), 99)
                if pct % 5 == 0:
                    pub_log(job_id, "render",
                        f"FFMPEG Final render {pct}%", pct=pct)
            except Exception:
                pass
    proc.wait()

    if proc.returncode != 0:
        err = proc.stderr.read().decode()[-500:]
        # BUG-1c FIX: If the final render failed (likely due to broken text
        # overlays or filter_complex), retry WITHOUT text overlays rather
        # than crashing the entire pipeline.
        if vf_final:
            pub_log(job_id, "render",
                f"FFMPEG Final render failed with text overlays, retrying without: {err[-100:]}")
            af_retry, maps_retry = _build_audio_filter(
                "", has_voice, has_music, has_sfx,
                voice_idx, music_idx, sfx_idx, duration
            )
            cmd_retry = [
                "ffmpeg", "-y",
                "-v", "warning",
                *inputs,
                *af_retry,
                *maps_retry,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-profile:v", "high" if fmt == "tv" else "main",
                "-preset", settings.ffmpeg_preset,
                "-b:v", spec["vb"],
                "-r", str(fps),
                "-t", str(duration),
                "-c:a", "aac",
                "-b:a", spec["ab"],
                "-ar", str(spec["ar"]),
                "-ac", "2",
                "-movflags", "+faststart",
                out_path
            ]
            result_retry = subprocess.run(cmd_retry, capture_output=True, timeout=900)
            if result_retry.returncode != 0:
                err2 = result_retry.stderr.decode()[-500:]
                raise RuntimeError(f"FFmpeg failed (even without overlays): {err2}")
        else:
            raise RuntimeError(f"FFmpeg failed: {err}")

    size_kb = os.path.getsize(out_path) // 1024
    pub_log(job_id, "render",
        f"FFMPEG ✓ {os.path.basename(out_path)} · {size_kb}KB · "
        f"{w}x{h} · {duration}s · {n_scenes} animated scenes",
        pct=100)
    pub_done(job_id, "render", time.time() - start)
    return out_path


def _validate_filter_string(vf: str) -> str:
    """Validate a video filter string before passing to FFmpeg.
    
    Returns the filter string if valid, or empty string if malformed.
    This prevents FFmpeg from crashing with 'Invalid argument' (-22).
    """
    if not vf:
        return ""
    stripped = vf.strip()
    if not stripped:
        return ""
    # Reject filters that start/end with separators
    if stripped.startswith((",", ";", "=")) or stripped.endswith((",", ";", "=")):
        return ""
    # Reject filters with empty text= fields (drawtext=...text='':... crashes)
    if "text=''" in stripped:
        return ""
    # Check for unbalanced single quotes (used in enable='...' and text='...')
    if stripped.count("'") % 2 != 0:
        return ""
    # Check for unbalanced parentheses in the filter
    depth = 0
    for ch in stripped:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if depth < 0:
            return ""  # More closing than opening parens
    if depth != 0:
        return ""  # Unclosed parentheses
    return stripped


def _build_audio_filter(vf_final, has_voice, has_music, has_sfx,
                        voice_idx, music_idx, sfx_idx, duration):
    """Build FFmpeg audio filter_complex and map arguments.
    
    Handles all combinations of voice, music, and SFX inputs.
    """
    # Defensive: validate video filter string before injecting into filter_complex
    vf_final = _validate_filter_string(vf_final)
    if has_voice and has_music and has_sfx:
        # All three: voice + music (ducked) + SFX
        sfx_vol = "volume=0.7"
        fc = (
            f"[0:v]{vf_final}[vout];" if vf_final else ""
        )
        fc += (
            f"[{voice_idx}:a]volume=1.0,asplit=2[voice1][voice2];"
            f"[{music_idx}:a]volume=0.5,atrim=0:{duration},aloop=loop=-1:size={int(44100 * float(duration))}[music_loop];"
            f"[music_loop][voice1]sidechaincompress=threshold=0.02:ratio=4:attack=200:release=800[music_ducked];"
            f"[{sfx_idx}:a]{sfx_vol}[sfx_vol];"
            f"[voice2][music_ducked][sfx_vol]amix=inputs=3:duration=first:dropout_transition=3[a]"
        )
        af = ["-filter_complex", fc]
        maps = ["-map", "[vout]" if vf_final else "0:v", "-map", "[a]"]

    elif has_voice and has_music:
        if vf_final:
            fc = (
                f"[0:v]{vf_final}[vout];"
                f"[{voice_idx}:a]volume=1.0,asplit=2[voice1][voice2];"
                f"[{music_idx}:a]volume=0.5,atrim=0:{duration},aloop=loop=-1:size={int(44100 * float(duration))}[music_loop];"
                f"[music_loop][voice1]sidechaincompress=threshold=0.02:ratio=4:attack=200:release=800[music_ducked];"
                f"[voice2][music_ducked]amix=inputs=2:duration=first:dropout_transition=3[a]"
            )
            af = ["-filter_complex", fc]
            maps = ["-map", "[vout]", "-map", "[a]"]
        else:
            fc = (
                f"[{voice_idx}:a]volume=1.0,asplit=2[voice1][voice2];"
                f"[{music_idx}:a]volume=0.5,atrim=0:{duration},aloop=loop=-1:size={int(44100 * float(duration))}[music_loop];"
                f"[music_loop][voice1]sidechaincompress=threshold=0.02:ratio=4:attack=200:release=800[music_ducked];"
                f"[voice2][music_ducked]amix=inputs=2:duration=first:dropout_transition=3[a]"
            )
            af = ["-filter_complex", fc]
            maps = ["-map", "0:v", "-map", "[a]"]

    elif has_voice and has_sfx:
        fc = (f"[0:v]{vf_final}[vout];" if vf_final else "")
        fc += (
            f"[{sfx_idx}:a]volume=0.7[sfx_vol];"
            f"[{voice_idx}:a][sfx_vol]amix=inputs=2:duration=first:dropout_transition=3[a]"
        )
        af = ["-filter_complex", fc]
        maps = ["-map", "[vout]" if vf_final else "0:v", "-map", "[a]"]

    elif has_voice:
        af = ["-filter_complex", f"[0:v]{vf_final}[vout]"] if vf_final else []
        maps = ["-map", "[vout]" if vf_final else "0:v", "-map", f"{voice_idx}:a"]

    elif has_music and has_sfx:
        fc = (f"[0:v]{vf_final}[vout];" if vf_final else "")
        fc += (
            f"[{sfx_idx}:a]volume=0.7[sfx_vol];"
            f"[{music_idx}:a][sfx_vol]amix=inputs=2:duration=first:dropout_transition=3[a]"
        )
        af = ["-filter_complex", fc]
        maps = ["-map", "[vout]" if vf_final else "0:v", "-map", "[a]"]

    elif has_music:
        af = ["-filter_complex", f"[0:v]{vf_final}[vout]"] if vf_final else []
        maps = ["-map", "[vout]" if vf_final else "0:v", "-map", f"{music_idx}:a"]

    elif has_sfx:
        af = ["-filter_complex", f"[0:v]{vf_final}[vout]"] if vf_final else []
        maps = ["-map", "[vout]" if vf_final else "0:v", "-map", f"{sfx_idx}:a"]

    else:
        af = ["-vf", vf_final] if vf_final else []
        maps = ["-map", "0:v"]

    return af, maps


def build_kinetic_typography(scenes, w, h, font_size):
    """Build kinetic typography drawtext filters for the ad.
    
    Phase 5 Enhanced: Purpose-aware animations, text shadow/outline,
    and scene-purpose-aware text placement.
    
    CRITICAL: FFmpeg drawtext's `fontsize` parameter only accepts
    integer constants, NOT expressions. Using if() there causes
    error code -22 (Invalid argument) and zero frames written.
    
    Animations by purpose:
    - hook: Large text, center-screen, with box background
    - problem: Slide-in from left, top area, medium
    - solution: Fade-in center, medium  
    - proof: Bottom-center, smaller
    - cta: Bounce vertically, center-bottom, gold, with box background
    """
    try:
        return _build_kinetic_typography_inner(scenes, w, h, font_size)
    except Exception as e:
        # NEVER let kinetic typography crash the pipeline
        print(f"build_kinetic_typography failed (non-fatal, skipping overlays): {e}")
        return ""


def _build_kinetic_typography_inner(scenes, w, h, font_size):
    """Inner implementation of kinetic typography. Separated so the outer
    wrapper can catch any exception and return empty string."""
    filters = []
    current_time = 0.0
    
    for scene in scenes:
        text = safe_text(scene.get("text_overlay", scene.get("text", "")), 35)
        duration_val = float(scene.get("duration", 0))
        if text and duration_val > 0:
            purpose = scene.get("purpose", "scene")
            
            # Purpose-aware animation parameters
            # NOTE: fontsize MUST be a plain integer — FFmpeg drawtext
            # does NOT support expressions in fontsize and will crash
            # with error code -22 (Invalid argument) if given one.
            if purpose == "hook":
                # Large text, center-screen, with box background
                actual_size = int(font_size * 1.3)
                x_expr = "(w-text_w)/2"
                y_expr = "(h-text_h)/2"
                color = "white"
                use_box = True
            elif purpose == "problem":
                # SLIDE-IN from left
                slide_dur = 0.5
                actual_size = font_size
                x_expr = f"if(lt(t-{current_time}\\\\,{slide_dur})\\\\,-text_w+(w/2+text_w)*(t-{current_time})/{slide_dur}\\\\,(w-text_w)/2)"
                y_expr = "80"
                color = "white"
                use_box = False
            elif purpose == "solution":
                # FADE-IN at center
                actual_size = font_size
                x_expr = "(w-text_w)/2"
                y_expr = "(h-text_h)/2"
                color = "white"
                use_box = False
            elif purpose == "proof":
                # Bottom-center, smaller
                actual_size = int(font_size * 0.85)
                x_expr = "(w-text_w)/2"
                y_expr = "h-120"
                color = "white"
                use_box = False
            elif purpose == "cta":
                # BOUNCE animation: text bounces vertically, gold color
                actual_size = int(font_size * 1.1)
                x_expr = "(w-text_w)/2"
                y_expr = f"h-100-15*abs(sin(5*(t-{current_time})))"
                color = "0xFFD700"
                use_box = True
            else:
                # Default: simple centered
                actual_size = font_size
                x_expr = "(w-text_w)/2"
                y_expr = "80"
                color = "white"
                use_box = False

            enable = f"between(t,{current_time},{current_time+duration_val})"
            
            # Shadow pass (deep black shadow offset by 4px for readability)
            # For simple expressions (no operators), just append +4
            # For complex expressions with operators, wrap in parens first
            has_ops = any(c in x_expr for c in "(+-*/")
            shadow_x = f"({x_expr})+4" if has_ops else f"{x_expr}+4"
            has_ops_y = any(c in y_expr for c in "(+-*/")
            shadow_y = f"({y_expr})+4" if has_ops_y else f"{y_expr}+4"
            shadow_f = (
                f"drawtext="
                f"{RESOLVED_FONT}"
                f"text='{text}':"
                f"fontsize={actual_size}:"
                f"fontcolor=black@0.9:"
                f"x={shadow_x}:y={shadow_y}:"
                f"enable='{enable}'"
            )
            filters.append(shadow_f)
            
            # Main text pass with optional box background
            box_args = ""
            if use_box:
                box_args = "box=1:boxcolor=black@0.7:boxborderw=12:"
            
            main_f = (
                f"drawtext="
                f"{RESOLVED_FONT}"
                f"text='{text}':"
                f"fontsize={actual_size}:"
                f"fontcolor={color}:"
                f"{box_args}"
                f"shadowcolor=black@0.8:"
                f"shadowx=3:shadowy=3:"
                f"x={x_expr}:y={y_expr}:"
                f"enable='{enable}'"
            )
            filters.append(main_f)
        
        current_time += duration_val
    
    result = ",".join(filters)
    # Final validation: if the resulting filter string is malformed, return empty
    return _validate_filter_string(result)


def _xfade_join(clips, output_dir, clip_durations, transitions_list):
    out = os.path.join(output_dir, "joined.mp4")

    n = len(clips)
    input_args = []
    for c in clips:
        input_args += ["-i", c]

    flt      = ""
    prev_lbl = "[0:v]"

    current_offset = 0.0
    xfade_duration = 0.5
    for i in range(1, n):
        # AI dictates the transition between clip i-1 and i. We use the transition assigned to clip i (the incoming clip).
        t   = transitions_list[i] if i < len(transitions_list) else "dissolve"
        # Resolve Motion Director transition name to FFmpeg xfade name
        t = _resolve_transition(t)
        lbl = f"[v{i:02d}]"
        
        # MOD-4 FIX: Correct xfade offset calculation.
        # Each xfade overlaps by xfade_duration seconds, so we subtract cumulative overlap.
        current_offset += clip_durations[i-1] - xfade_duration
        # Ensure offset is never negative
        current_offset = max(0.0, current_offset)
        
        flt += (
            f"{prev_lbl}[{i}:v]"
            f"xfade=transition={t}:duration={xfade_duration}:"
            f"offset={current_offset:.2f}"
            f"{lbl};"
        )
        prev_lbl = lbl

    flt = flt.rstrip(";")

    cmd = [
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", flt,
        "-map", prev_lbl,
        "-c:v", "libx264",
        "-preset", settings.ffmpeg_preset,
        "-an", out
    ]

    result = subprocess.run(cmd, capture_output=True, timeout=900)
    if result.returncode != 0:
        return _concat_join(clips, output_dir)
    return out


def _concat_join(clips, output_dir):
    lst = os.path.join(output_dir, "concat.txt")
    out = os.path.join(output_dir, "joined.mp4")
    with open(lst, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", lst,
        "-c", "copy", out
    ], capture_output=True, timeout=900)
    return out


def _static_clip(img_path, duration, w, h, output_dir, idx, fps=30):
    out = os.path.join(output_dir, f"clip_{idx:02d}.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration + 0.6),
        "-i", img_path,
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
               f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p",
        "-c:v", "libx264", "-preset", settings.ffmpeg_preset,
        "-r", str(fps),
        "-t", str(duration + 0.6), "-an", out
    ], capture_output=True, timeout=900)
    return out
