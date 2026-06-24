"""
10. Real Motion Video Planner
"""
import requests, json
from config import settings
from schemas.advanced_agent_schemas import RealMotionVideoPlannerOutput

def plan_motion_video(storyboard: dict, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are a Commercial Film Director.

Convert storyboard scenes into motion plans.

For every shot determine:
camera movement
movement speed
focus target
transition
cinematic purpose

Storyboard:
{json.dumps(storyboard, indent=2)}

Return JSON only matching exactly this format:
{{
  "shots":[
    {{
      "scene":1,
      "camera_movement":"",
      "speed":"",
      "focus_target":"",
      "transition":"",
      "purpose":""
    }}
  ]
}}"""

    r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
        "model": getattr(settings, "ollama_model", model_name),
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.6}
    }, timeout=settings.ollama_request_timeout)

    try:
        raw = r.json().get("response", "")
        output = RealMotionVideoPlannerOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Motion Video Planner Error: {e}")
        return {"shots": []}
