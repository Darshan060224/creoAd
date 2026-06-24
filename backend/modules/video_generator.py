"""
Stage B5: Generate video clips from images (Wan2.1 / LTX via ComfyUI)
"""

import requests
import time
import os
from pathlib import Path
from typing import Optional

try:
    from ..config import settings
    from ..pipeline.progress import pub_log
except ImportError:
    from config import settings
    from pipeline.progress import pub_log

from .image_generator import _resolve_checkpoint_name, _download_comfyui_file, _extract_history_record

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

def generate_video_clip(image_path: str, camera_motion: str, duration: float, scene_id: int, output_dir: str, job_id: str = "unknown") -> Optional[str]:
    """
    Generate an AI video clip from an image using ComfyUI.
    """
    output_dir_path = Path(output_dir)
    
    # Workflow placeholder for Wan2.1/LTX image-to-video
    # This assumes a generic node setup. If ComfyUI video models aren't present,
    # it fails and fallback to ffmpeg will occur.
    workflow = {
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": image_path
            }
        },
        "2": {
            "class_type": "VideoModelLoader",
            "inputs": {
                "ckpt_name": "wan2.1_video.safetensors"
            }
        },
        "3": {
            "class_type": "VideoGenerator",
            "inputs": {
                "model": ["2", 0],
                "image": ["1", 0],
                "motion_type": camera_motion,
                "duration": duration
            }
        },
        "4": {
            "class_type": "SaveAnimatedWEBP", # or SaveVideo
            "inputs": {
                "filename_prefix": f"creoad_video_{scene_id:02d}",
                "images": ["3", 0],
                "fps": 30
            }
        }
    }
    
    try:
        response = requests.post(
            f"{settings.comfyui_url}/api/prompt",
            json={
                "prompt": workflow,
                "client_id": "creoad-video-backend",
            },
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        prompt_id = result.get('prompt_id')
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return a prompt_id")
            
        max_wait = 600 # 10 min for video
        waited = 0
        record = {}
        while waited < max_wait:
            status_response = requests.get(
                f"{settings.comfyui_url}/api/history/{prompt_id}",
                timeout=10
            )
            
            if status_response.ok:
                history = status_response.json()
                record = _extract_history_record(history, prompt_id)
                if record.get('outputs'):
                    break
            
            time.sleep(5)
            waited += 5
            
        if waited >= max_wait:
            raise TimeoutError("ComfyUI video generation timed out")
            
        video_info = _extract_output_video(record)
        filename = video_info.get("filename")
        subfolder = video_info.get("subfolder", "")
        file_type = video_info.get("type", "output")

        if not filename:
            raise RuntimeError("ComfyUI finished but no video filename was found in output")

        local_video_path = output_dir_path / f"video_clip_{scene_id:02d}.mp4" # Or webp depending on node
        _download_comfyui_file(filename, subfolder, file_type, local_video_path)
        return str(local_video_path)
        
    except Exception as e:
        # Fail explicitly instead of silent fallback
        raise RuntimeError(f"AI Video Generation Failed: {e}")
