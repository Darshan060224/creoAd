"""
Day 2 — Marketing Strategist
Model: deepseek-r1
"""
import requests, json
from config import settings
from schemas.agent_schemas import MarketingOutput

def create_marketing_strategy(brand_data: dict, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are a world-class advertising strategist.

Using the provided brand data generate:
- hook
- problem
- agitation
- solution
- social_proof
- call_to_action

Use PAS framework.

Brand Data:
{json.dumps(brand_data, indent=2)}

Return JSON only matching exactly this format:
{{
  "hook":"",
  "problem":"",
  "agitation":"",
  "solution":"",
  "social_proof":"",
  "cta":""
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
        output = MarketingOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Marketing Strategist Error: {e}")
        return {
            "hook": "Are you struggling?",
            "problem": "It's hard.",
            "agitation": "It gets worse over time.",
            "solution": "We can help.",
            "social_proof": "Trusted by thousands.",
            "cta": "Get started today."
        }
