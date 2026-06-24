"""
Phase 3 - Competitor Agent
"""
import requests, json
from config import settings
from schemas.marketing_schemas import CompetitorAgentOutput

def analyze_competitors(industry: str, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are a Competitor Intelligence Analyst.

Analyze the leading competitors in the following industry:
{industry}

Identify their strengths, weaknesses, and current offers.

Return JSON only matching exactly this format:
{{
  "competitors": [
    {{
      "competitor_name": "",
      "strengths": [],
      "weaknesses": [],
      "current_offers": []
    }}
  ]
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
        output = CompetitorAgentOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Competitor Agent Error: {e}")
        return {"competitors": []}
