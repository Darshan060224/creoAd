"""
7. Self-Improvement Loop Agent
"""
import requests, json
from config import settings
from schemas.advanced_agent_schemas import SelfImprovementOutput

def extract_campaign_lessons(performance_data: dict, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are a Continuous Improvement System.

Analyze completed campaigns.

Performance Data:
{json.dumps(performance_data, indent=2)}

Identify:
what worked
what failed
patterns
recommendations

Generate lessons that should be stored for future campaigns.

Return JSON only matching exactly this format:
{{
  "success_patterns":[],
  "failure_patterns":[],
  "recommendations":[],
  "future_rules":[]
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
        output = SelfImprovementOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Self-Improvement Agent Error: {e}")
        return {"success_patterns": [], "failure_patterns": [], "recommendations": [], "future_rules": []}
