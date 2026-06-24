"""
4. Visual Continuity Engine
"""
import requests, json
from config import settings
from schemas.advanced_agent_schemas import VisualContinuityOutput

def maintain_visual_continuity(creative_brief: dict, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are a Visual Consistency Supervisor.

Maintain visual continuity across all scenes.

Creative Brief:
{json.dumps(creative_brief, indent=2)}

Track:
location
lighting
weather
camera style
wardrobe
color palette
time of day
visual mood

Ensure consistency between scenes.

Return JSON only matching exactly this format:
{{
  "continuity_rules":{{
    "location":"",
    "lighting":"",
    "weather":"",
    "camera_style":"",
    "wardrobe":"",
    "color_palette":[],
    "time_of_day":"",
    "visual_mood":""
  }}
}}"""

    r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
        "model": getattr(settings, "ollama_model", model_name),
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.5}
    }, timeout=settings.ollama_request_timeout)

    try:
        raw = r.json().get("response", "")
        output = VisualContinuityOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Visual Continuity Engine Error: {e}")
        return {"continuity_rules": {}}
