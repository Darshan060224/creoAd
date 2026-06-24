"""
2. Emotional Arc Planner
"""
import requests, json
from config import settings
from schemas.advanced_agent_schemas import EmotionalArcOutput

def plan_emotional_arc(creative_brief: dict, num_scenes: int, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are a Commercial Storytelling Director.

Design the emotional journey of an advertisement.
Create a scene-by-scene emotional progression for {num_scenes} scenes.

Creative Brief:
{json.dumps(creative_brief, indent=2)}

Possible emotions:
Curiosity, Shock, Pain, Frustration, Hope, Desire, Trust, Excitement, Urgency, Confidence, Action

Rules:
Build emotional momentum.
Avoid flat emotional curves.
Ensure the final scene drives action.

Return JSON only matching exactly this format:
{{
  "emotional_arc":[
    {{
      "scene":1,
      "emotion":"",
      "reason":""
    }}
  ]
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
        output = EmotionalArcOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Emotional Arc Agent Error: {e}")
        return {"emotional_arc": []}
