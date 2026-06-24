"""
Day 4 — Audience Agent
Model: qwen3
"""
import requests, json
from config import settings
from schemas.agent_schemas import AudienceOutput

def segment_audience(brand_data: dict, model_name: str = "qwen3") -> dict:
    prompt = f"""You are a Master Market Researcher.
Segment the audience for this brand into 3-5 distinct, highly-detailed personas.

For each segment generate:
- audience_name (e.g. "Busy Professionals", "Students")
- persona_description (1-2 sentences describing their daily life)
- pain_points (List of specific problems they face)
- desires (List of outcomes they deeply want)
- objections (List of reasons they might not buy)

Brand Data:
{json.dumps(brand_data, indent=2)}

Return JSON only matching exactly this format:
{{
  "audiences":[
    {{
      "audience_name": "",
      "persona_description": "",
      "pain_points": [],
      "desires": [],
      "objections": []
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
        output = AudienceOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Audience Agent Error: {e}")
        return {"audiences": []}
