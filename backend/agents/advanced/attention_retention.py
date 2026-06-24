"""
9. Attention Retention Engine
"""
import requests, json
from config import settings
from schemas.advanced_agent_schemas import AttentionRetentionOutput

def predict_retention(script: dict, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are a Video Retention Analyst.

Predict where viewers may lose interest.

Analyze:
hook strength
pacing
visual variety
emotional engagement
CTA timing

Ad Script / Scenes:
{json.dumps(script, indent=2)}

Return JSON only matching exactly this format:
{{
  "retention_score":0.0,
  "hook_score":0.0,
  "pacing_score":0.0,
  "engagement_score":0.0,
  "cta_score":0.0,
  "dropoff_risks":[],
  "recommendations":[]
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
        output = AttentionRetentionOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Retention Engine Error: {e}")
        return {
            "retention_score": 0.0, "hook_score": 0.0, "pacing_score": 0.0,
            "engagement_score": 0.0, "cta_score": 0.0, "dropoff_risks": [], "recommendations": []
        }
