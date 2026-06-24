import requests
workflow = {
    "1": { "class_type": "CheckpointLoaderSimple", "inputs": { "ckpt_name": "sdxl_turbo_fp16.safetensors" } },
    "2": { "class_type": "CLIPTextEncode", "inputs": { "text": "test", "clip": ["1", 1] } },
    "3": { "class_type": "CLIPTextEncode", "inputs": { "text": "", "clip": ["1", 1] } },
    "4": { "class_type": "EmptyLatentImage", "inputs": { "width": 1024, "height": 576, "batch_size": 1 } },
    "5": { "class_type": "KSampler", "inputs": { "seed": 42, "steps": 4, "cfg": 1.5, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0] } },
    "6": { "class_type": "VAEDecode", "inputs": { "samples": ["5", 0], "vae": ["1", 2] } },
    "7": { "class_type": "SaveImage", "inputs": { "filename_prefix": "creoad_scene_01", "images": ["6", 0] } }
}
r = requests.post("http://localhost:8188/api/prompt", json={"prompt": workflow})
print(r.status_code)
print(r.text)
