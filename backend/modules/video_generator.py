"""
Stage B5: Generate video clips from images (Wan2.1 / LTX via ComfyUI)

Pre-flight checks ensure we only send valid workflows to ComfyUI.
If the required video model weights are not installed, we return None
immediately so the caller can fall back to Ken Burns FFmpeg animation.
"""

import requests
import time
import os
from pathlib import Path
from typing import Optional, List

try:
    from ..config import settings
    from ..pipeline.progress import pub_log
except ImportError:
    from config import settings
    from pipeline.progress import pub_log

from .image_generator import _resolve_checkpoint_name, _download_comfyui_file, _extract_history_record


# Paths where Wan2.1 / LTX video model weights would live
_MODELS_ROOT = Path(__file__).resolve().parents[2] / "modals" / "ComfyUI" / "models"
_VIDEO_MODEL_DIRS = [
    _MODELS_ROOT / "diffusion_models",
    _MODELS_ROOT / "checkpoints",
]

# Known Wan2.1 video model filename patterns
_WAN_VIDEO_PATTERNS = [
    "wan2.1*",
    "wan_2.1*",
    "wan21*",
    "ltx*video*",
]


def _find_video_model() -> Optional[str]:
    """Scan model directories for a video model file. Returns the filename or None."""
    for model_dir in _VIDEO_MODEL_DIRS:
        if not model_dir.exists():
            continue
        for pattern in _WAN_VIDEO_PATTERNS:
            matches = sorted(model_dir.glob(pattern))
            if matches:
                return matches[0].name
    return None


def _check_comfyui_has_node(node_type: str) -> bool:
    """Check if ComfyUI has a specific node type available."""
    try:
        resp = requests.get(
            f"{settings.comfyui_url}/object_info/{node_type}",
            timeout=5,
        )
        if resp.ok:
            data = resp.json()
            return node_type in data
    except Exception:
        pass
    return False


def _extract_output_video(record: dict) -> dict:
    outputs = record.get("outputs", {})
    for node_output in outputs.values():
        gifs = node_output.get("gifs", [])
        if gifs:
            return gifs[0]
        # Some nodes might return videos in a "videos" array or similar
        videos = node_output.get("videos", [])
        if videos:
            return videos[0]
    return {}


def generate_video_clip(
    image_path: str,
    camera_motion: str,
    duration: float,
    scene_id: int,
    output_dir: str,
    job_id: str = "unknown",
) -> Optional[str]:
    """
    Generate an AI video clip from an image using ComfyUI.

    Pre-flight checks:
    1. Verify video model weights are installed locally.
    2. Verify ComfyUI has the required node type.
    If either check fails, return None so the caller falls back to Ken Burns.
    """
    output_dir_path = Path(output_dir)

    # ── Pre-flight: check for video model weights ──
    video_model = _find_video_model()
    if not video_model:
        pub_log(
            job_id,
            "render",
            f"VideoGen ⚠ No video model weights found in {_VIDEO_MODEL_DIRS[0]} — skipping AI video for scene {scene_id}",
        )
        return None

    # ── Pre-flight: check ComfyUI has WanImageToVideo node ──
    if not _check_comfyui_has_node("WanImageToVideo"):
        pub_log(
            job_id,
            "render",
            f"VideoGen ⚠ ComfyUI missing WanImageToVideo node — skipping AI video for scene {scene_id}",
        )
        return None

    # ── Build a real Wan2.1 Image-to-Video workflow ──
    # Calculate frame count: Wan2.1 expects length in frames (multiples of 4 + 1)
    fps = 16  # Wan2.1 native fps
    raw_frames = max(17, int(duration * fps))
    # Round to nearest valid length (multiple of 4, plus 1)
    length = ((raw_frames - 1) // 4) * 4 + 1

    # Map camera_motion to a text prompt for the video model
    motion_prompts = {
        "zoom_in": "smooth camera slowly zooming in",
        "zoom_out": "smooth camera slowly zooming out",
        "pan_right": "smooth camera panning right",
        "pan_left": "smooth camera panning left",
        "pan_up": "smooth camera tilting up",
        "pan_down": "smooth camera tilting down",
        "push_in": "camera pushing forward into the scene",
        "pull_out": "camera pulling back from the scene",
        "orbit_left": "camera orbiting left around the subject",
        "orbit_right": "camera orbiting right around the subject",
        "parallax": "subtle parallax camera movement",
        "dolly_in": "camera dolly moving forward",
        "drone": "aerial drone camera slowly rising",
        "static": "static camera, subtle ambient motion",
        "none": "static camera, subtle ambient motion",
    }
    motion_text = motion_prompts.get(camera_motion, "smooth cinematic camera movement")
    prompt_text = f"cinematic commercial footage, {motion_text}, high quality, 4K, professional lighting"
    negative_text = "blurry, low quality, distorted, glitch, watermark, text"

    workflow = {
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": os.path.basename(image_path),
                "upload": "image",
            },
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "t5xxl_fp16.safetensors",
                "type": "wan",
            },
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt_text,
                "clip": ["2", 0],
            },
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative_text,
                "clip": ["2", 0],
            },
        },
        "5": {
            "class_type": "CLIPVisionLoader",
            "inputs": {
                "clip_name": "clip_vision_h.safetensors",
            },
        },
        "6": {
            "class_type": "CLIPVisionEncode",
            "inputs": {
                "clip_vision": ["5", 0],
                "image": ["1", 0],
            },
        },
        "7": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": video_model,
                "weight_dtype": "default",
            },
        },
        "8": {
            "class_type": "ModelSamplingSD3",
            "inputs": {
                "model": ["7", 0],
                "shift": 5.0,
            },
        },
        "9": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "wan_2.1_vae.safetensors",
            },
        },
        "10": {
            "class_type": "WanImageToVideo",
            "inputs": {
                "positive": ["3", 0],
                "negative": ["4", 0],
                "vae": ["9", 0],
                "width": 832,
                "height": 480,
                "length": length,
                "batch_size": 1,
                "clip_vision_output": ["6", 0],
                "start_image": ["1", 0],
            },
        },
        "11": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 42 + scene_id,
                "steps": 20,
                "cfg": 3.0,
                "sampler_name": "uni_pc",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["8", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["10", 0],
            },
        },
        "12": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["11", 0],
                "vae": ["9", 0],
            },
        },
        "13": {
            "class_type": "SaveAnimatedWEBP",
            "inputs": {
                "filename_prefix": f"creoad_video_{scene_id:02d}",
                "images": ["12", 0],
                "fps": fps,
                "lossless": False,
                "quality": 80,
                "method": "default",
            },
        },
    }

    try:
        # Upload the source image to ComfyUI first
        try:
            with open(image_path, "rb") as f:
                upload_resp = requests.post(
                    f"{settings.comfyui_url}/upload/image",
                    files={"image": (os.path.basename(image_path), f, "image/png")},
                    data={"overwrite": "true"},
                    timeout=30,
                )
                upload_resp.raise_for_status()
        except Exception as upload_err:
            pub_log(job_id, "render", f"VideoGen ⚠ Failed to upload image to ComfyUI: {upload_err}")
            return None

        response = requests.post(
            f"{settings.comfyui_url}/api/prompt",
            json={
                "prompt": workflow,
                "client_id": "creoad-video-backend",
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()

        prompt_id = result.get("prompt_id")
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return a prompt_id")

        max_wait = 600  # 10 min for video
        waited = 0
        record = {}
        while waited < max_wait:
            status_response = requests.get(
                f"{settings.comfyui_url}/api/history/{prompt_id}",
                timeout=10,
            )

            if status_response.ok:
                history = status_response.json()
                record = _extract_history_record(history, prompt_id)
                if record.get("outputs"):
                    break
                # Check for errors in the execution
                status_info = record.get("status", {})
                if status_info.get("status_str") == "error":
                    error_msgs = status_info.get("messages", [])
                    raise RuntimeError(f"ComfyUI execution error: {error_msgs}")

            time.sleep(5)
            waited += 5

        if waited >= max_wait:
            raise TimeoutError("ComfyUI video generation timed out")

        video_info = _extract_output_video(record)
        filename = video_info.get("filename")
        subfolder = video_info.get("subfolder", "")
        file_type = video_info.get("type", "output")

        if not filename:
            raise RuntimeError(
                "ComfyUI finished but no video filename was found in output"
            )

        local_video_path = output_dir_path / f"video_clip_{scene_id:02d}.webp"
        _download_comfyui_file(filename, subfolder, file_type, local_video_path)

        # Convert webp to mp4 for compatibility with the rest of the pipeline
        mp4_path = output_dir_path / f"video_clip_{scene_id:02d}.mp4"
        import subprocess
        conv_result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(local_video_path),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", "30",
                "-an",
                str(mp4_path),
            ],
            capture_output=True,
            timeout=120,
        )
        if conv_result.returncode == 0 and mp4_path.exists():
            return str(mp4_path)
        else:
            # If conversion fails, still return the webp
            return str(local_video_path)

    except Exception as e:
        # Fail explicitly so the caller can decide on fallback
        raise RuntimeError(f"AI Video Generation Failed: {e}")
