from pathlib import Path
import os
COMFYUI_MODELS_ROOT = Path("/home/da24/Desktop/creoAd/backend/modules/image_generator.py").resolve().parents[2] / "modals" / "ComfyUI" / "models"
checkpoint_name = "sdxl_turbo_fp16.safetensors"
path = COMFYUI_MODELS_ROOT / "checkpoints" / checkpoint_name
print(f"Path: {path}")
print(f"Exists: {path.exists()}")
