"""
Day 5 — Creative Director
Model: deepseek-r1
"""
import requests, json
from config import settings
from schemas.agent_schemas import CreativeDirectorOutput

def create_brief(brand_profile: dict, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are an award-winning creative director.

Design the visual identity.

Brand Data:
{json.dumps(brand_profile, indent=2)}

Return JSON only matching exactly this format:
{{
 "theme":"",
 "mood":"",
 "color_palette":[],
 "camera_style":"",
 "editing_style":"",
 "music_style":""
}}"""

    r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
        "model": getattr(settings, "ollama_model", model_name),
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.7}
    }, timeout=settings.ollama_request_timeout)

    try:
        raw = r.json().get("response", "")
        output = CreativeDirectorOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Creative Director Error: {e}")
        return {
            "theme": "Trust",
            "mood": "Aspiration",
            "color_palette": ["#1a1a2e", "#4f46e5", "#ffffff"],
            "camera_style": "Slow cinematic",
            "editing_style": "Smooth cuts",
            "music_style": "Uplifting"
        }
