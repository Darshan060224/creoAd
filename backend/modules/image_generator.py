"""
Stage B2: Generate scene images using ComfyUI + Stable Diffusion
"""

import requests
import time
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

try:
    from ..config import settings
    from ..pipeline.progress import pub_start, pub_log, pub_done, pub_error
except ImportError:
    from config import settings
    from pipeline.progress import pub_start, pub_log, pub_done, pub_error

try:
    from .face_consistency import inject_face_consistency
except ImportError:
    from face_consistency import inject_face_consistency


COMFYUI_MODELS_ROOT = Path(__file__).resolve().parents[2] / "modals" / "ComfyUI" / "models"


def _find_first_model_file(folder_name: str, patterns: List[str]) -> str:
    folder_path = COMFYUI_MODELS_ROOT / folder_name
    if not folder_path.exists():
        return ""

    for pattern in patterns:
        matches = sorted(folder_path.glob(pattern))
        if matches:
            return matches[0].name

    return ""


def _resolve_checkpoint_name() -> str:
    configured_name = getattr(settings, "comfyui_checkpoint", "") if hasattr(settings, "comfyui_checkpoint") else ""
    if configured_name:
        configured_path = COMFYUI_MODELS_ROOT / "checkpoints" / configured_name.strip()
        if configured_path.exists():
            return configured_path.name

    preferred_names = [
        "sdxl_turbo_fp16.safetensors",
        "sdxl_turbo.safetensors",
        "sd_xl_turbo_1.0.safetensors",
    ]
    for name in preferred_names:
        candidate = COMFYUI_MODELS_ROOT / "checkpoints" / name
        if candidate.exists():
            return candidate.name

    checkpoint_name = _find_first_model_file("checkpoints", ["*.safetensors", "*.ckpt", "*.pt"])
    if checkpoint_name:
        return checkpoint_name

    return configured_name.strip()


def _download_comfyui_file(filename: str, subfolder: str, file_type: str, output_path: Path) -> None:
    response = requests.get(
        f"{settings.comfyui_url}/api/view",
        params={
            "filename": filename,
            "subfolder": subfolder,
            "type": file_type,
        },
        timeout=settings.ollama_request_timeout,
    )
    response.raise_for_status()
    output_path.write_bytes(response.content)


def _extract_history_record(history_payload: dict, prompt_id: str) -> dict:
    if prompt_id in history_payload:
        return history_payload[prompt_id]

    if history_payload.get("prompt_id") == prompt_id:
        return history_payload

    return {}


def _extract_output_image(record: dict) -> dict:
    outputs = record.get("outputs", {})
    for node_output in outputs.values():
        images = node_output.get("images", [])
        if images:
            return images[0]

    return {}

def generate_scene_images(descriptions: List[str], output_dir: str, job_id: str = "unknown", workflows: List[str] = None, ip_adapter_image: str = None) -> List[str]:
    """
    Generate images for each scene using ComfyUI
    
    Args:
        descriptions: List of scene descriptions (prompts)
        output_dir: Where to save images
        job_id: The job ID for UI logging
        workflows: List of workflow names (same length as descriptions)
        ip_adapter_image: Path to reference face image for character consistency (IPAdapter)
    
    Returns:
        List of image file paths
    """
    import time
    start_time = time.time()
    pub_start(job_id, "images", "ComfyUI :8188 · SDXL-Turbo")
    
    if not test_comfyui_connection():
        pub_log(job_id, "images", "COMFY ✗ Not reachable at :8188 · Run: python main.py --port 8188", pct=0)
        print("ComfyUI not reachable — using placeholder images")
        paths = [create_placeholder_image(i, output_dir) for i in range(len(descriptions))]
        pub_done(job_id, "images", time.time() - start_time)
        return paths

    checkpoint_name = _resolve_checkpoint_name() or "sdxl_turbo"
    pub_log(job_id, "images", f"COMFY Connected · generating {len(descriptions)} scenes · model={checkpoint_name}", pct=5)
    pub_log(job_id, "images", f"COMFY Settings: steps={getattr(settings, 'comfyui_steps', 4)} · cfg={getattr(settings, 'comfyui_cfg', 1.5)} · {getattr(settings, 'comfyui_width', 1024)}x{getattr(settings, 'comfyui_height', 576)}", pct=8)

    image_paths = [None] * len(descriptions)

    max_workers = min(len(descriptions), os.cpu_count() or 4)
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
        future_map = {
            executor.submit(generate_single_image, description, i, output_dir, workflows[i] if workflows and i < len(workflows) else "general", None, ip_adapter_image): i
            for i, description in enumerate(descriptions)
        }

        for future in as_completed(future_map):
            index = future_map[future]
            try:
                image_paths[index] = future.result()
                print(f"Generated scene {index + 1} image: {image_paths[index]}")
            except Exception as e:
                print(f"Error generating scene {index + 1}: {str(e)}")
                image_paths[index] = create_placeholder_image(index, output_dir)
            
            done += 1
            scene_desc = descriptions[index][:50]
            pub_log(job_id, "images", f"COMFY ✓ scene_{index:02d}.png · \"{scene_desc}...\"", pct=int((done / len(descriptions)) * 100))

    pub_done(job_id, "images", time.time() - start_time)
    return [path for path in image_paths if path]

def generate_single_image(prompt: str, scene_id: int, output_dir: str, workflow_name: str = "general", negative_prompt: str = None, ip_adapter_image: str = None) -> str:
    """Generate a single image using ComfyUI API with a specific workflow"""
    
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(exist_ok=True)

    checkpoint_name = _resolve_checkpoint_name()
    if not checkpoint_name:
        # No local checkpoint is available in this environment. Return a
        # deterministic placeholder frame instead of failing the whole stage.
        return create_placeholder_image(scene_id, output_dir)
    
    # The "Secret Sauce" for commercial images
    enhanced_prompt = f"{prompt}, cinematic lighting, commercial advertising photography, 8k, ultra detailed, professional product photography, depth of field, global illumination, volumetric lighting, premium quality, sharp focus, shot on 35mm lens."
    
    if not negative_prompt:
        negative_prompt = (
            "cartoon, illustration, anime, blurry, low quality, distorted, text, watermark, logo, deformed, low resolution."
        )

    width = getattr(settings, "comfyui_width", 1024)
    height = getattr(settings, "comfyui_height", 576)
    steps = getattr(settings, "comfyui_steps", 8)
    cfg = getattr(settings, "comfyui_cfg", 2.5)
    sampler_name = getattr(settings, "comfyui_sampler", "euler_ancestral")

    # Standard ComfyUI txt2img workflow.
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": checkpoint_name,
            }
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": enhanced_prompt,
                "clip": ["1", 1],
            }
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative_prompt,
                "clip": ["1", 1],
            }
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1,
            }
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 42 + scene_id,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler_name,
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            }
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["5", 0],
                "vae": ["1", 2],
            }
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": f"creoad_scene_{scene_id:02d}",
                "images": ["6", 0],
            }
        }
    }
    
    if ip_adapter_image and os.path.exists(ip_adapter_image):
        try:
            workflow = inject_face_consistency(workflow, ip_adapter_image)
            print(f"Injected Face Consistency (IPAdapter) for scene {scene_id} using reference {ip_adapter_image}")
        except Exception as e:
            print(f"Warning: Failed to inject Face Consistency for scene {scene_id}: {e}")
            
    try:
        if checkpoint_name and not (COMFYUI_MODELS_ROOT / "checkpoints" / checkpoint_name).exists():
            return create_placeholder_image(scene_id, output_dir)

        # Send to ComfyUI
        response = requests.post(
            f"{settings.comfyui_url}/api/prompt",
            json={
                "prompt": workflow,
                "client_id": "creoad-backend",
                "extra_data": {
                    "scene_id": scene_id,
                    "source_prompt": prompt,
                    "ip_adapter_image": ip_adapter_image
                },
            },
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Wait for image generation
        prompt_id = result.get('prompt_id')
        if not prompt_id:
            raise Exception("No prompt ID returned from ComfyUI")
        
        # Poll for completion (timeout after 10 min)
        max_wait = 300
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
            
            time.sleep(2)
            waited += 2
        
        if waited >= max_wait:
            raise Exception("Image generation timeout")
        
        image_info = _extract_output_image(record)
        filename = image_info.get("filename")
        subfolder = image_info.get("subfolder", "")
        file_type = image_info.get("type", "output")

        if not filename:
            raise Exception("ComfyUI completed without returning an output image")

        local_image_path = output_dir_path / f"scene_{scene_id:02d}.png"
        _download_comfyui_file(filename, subfolder, file_type, local_image_path)
        return str(local_image_path)
    
    except Exception as e:
        # Fallback to placeholder
        return create_placeholder_image(scene_id, output_dir)

def create_placeholder_image(scene_id: int, output_dir: str) -> str:
    """Create a placeholder image if generation fails"""
    from PIL import Image, ImageDraw
    import re
    import os

    PALETTES = [
        [(15,23,42),   (30,64,175),  (99,179,237)],
        [(5,46,22),    (21,128,61),  (74,222,128)],
        [(42,15,15),   (185,28,28),  (252,165,165)],
        [(42,15,60),   (126,34,206), (196,181,253)],
        [(15,42,42),   (6,148,162),  (103,232,249)],
    ]
    # L9 FIX: Use configured resolution instead of hardcoded 1024x576
    W = getattr(settings, "comfyui_width", 1024)
    H = getattr(settings, "comfyui_height", 576)
    pal   = PALETTES[scene_id % len(PALETTES)]
    dark, mid, light = pal

    img  = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    for y in range(H):
        t = y / H
        r = int(dark[0] + (mid[0]-dark[0]) * t)
        g = int(dark[1] + (mid[1]-dark[1]) * t)
        b = int(dark[2] + (mid[2]-dark[2]) * t)
        draw.line([(0,y),(W,y)], fill=(r,g,b))

    draw.ellipse([W-200,-80,W+80,200], outline=light, width=2)
    draw.ellipse([-80,H-200,200,H+80], outline=light, width=2)

    for y in range(0, H, 60):
        draw.line([(0,y),(W,y)], fill=(255,255,255,8), width=1)

    for x in range(W):
        t = x/W
        draw.line([(x,H-5),(x,H)], fill=(
            int(light[0]*t), int(light[1]*t), int(light[2]*t)
        ))

    text = f"Scene {scene_id+1}"
    try:
        import json
        script_path = os.path.join(output_dir, "script.json")
        with open(script_path, "r") as f:
            script_data = json.load(f)
            scenes = script_data.get("scenes", [])
            if scene_id < len(scenes):
                text_overlay = scenes[scene_id].get("text_overlay", "")
                if text_overlay: text = text_overlay
    except Exception:
        pass

    text = re.sub(r"['\"\`]", "", str(text))[:40]
    draw.text((W//2, H-40), text, fill=(255,255,255), anchor="mm")

    path = os.path.join(output_dir, f"scene_{scene_id:02d}.png")
    img.save(path)
    return path

def test_comfyui_connection() -> bool:
    """Test if ComfyUI is running"""
    try:
        response = requests.get(
            f"{settings.comfyui_url}/system_stats",
            timeout=3
        )
        return response.ok
    except Exception:
        return False
