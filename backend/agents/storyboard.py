"""
Day 6 — Storyboard Agent
Model: deepseek-r1 (or fallback)
"""
import requests, json
from config import settings
from schemas.agent_schemas import StoryboardOutput

def create_storyboard(marketing_strategy: dict, creative_brief: dict, duration: int = 30, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""Create a storyboard.

Rules:
{duration} seconds total.

Scenes must include:
Hook, Problem, Solution, Proof, CTA

Strategy:
{json.dumps(marketing_strategy, indent=2)}

Creative Brief:
{json.dumps(creative_brief, indent=2)}

Return JSON only matching exactly this format:
{{
  "scenes":[
    {{
      "scene_number": 1,
      "duration": 6,
      "hook": "",
      "problem": "",
      "solution": "",
      "proof": "",
      "cta": "",
      "description": ""
    }}
  ]
}}"""

    r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
        "model": getattr(settings, "ollama_model", model_name),
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.7}
    }, timeout=90)

    try:
        raw = r.json().get("response", "")
        output = StoryboardOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Storyboard Agent Error: {e}")
        return {"scenes": []}
