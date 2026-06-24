"""
Day 7 — Shot Planner
Model: deepseek-r1
"""
import requests, json
from config import settings
from schemas.agent_schemas import ShotPlannerOutput

def plan_shots(storyboard: dict, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are a Hollywood cinematographer and Dynamic Shot Planner.

For each scene, analyze the emotion and generate a shot list:
- shot_count (Dynamic based on pacing: Fast=many, Slow=few)
- shot_duration (Must sum exactly to scene duration)
- camera_type (e.g. closeup, wide, medium)
- camera_motion (e.g. pan left, push in, static, drone flyover)
- composition (e.g. rule of thirds, symmetric)

Total duration of all shots in a scene MUST match the scene duration perfectly.

Storyboard:
{json.dumps(storyboard, indent=2)}

Return JSON only matching exactly this format:
{{
  "scenes": {{
    "scene_1": {{
      "shots": [
        {{
          "shot_count": 1,
          "shot_duration": 5.0,
          "camera_type": "wide angle",
          "camera_motion": "push in slowly",
          "composition": "rule of thirds"
        }}
      ]
    }}
  }}
}}"""

    r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
        "model": getattr(settings, "ollama_model", model_name),
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.6}
    }, timeout=90)

    try:
        raw = r.json().get("response", "")
        output = ShotPlannerOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Shot Planner Error: {e}")
        return {"scenes": {}}
