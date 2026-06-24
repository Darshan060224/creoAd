"""
Phase 3 - CTA Generator
"""
import requests, json
from config import settings
from schemas.marketing_schemas import CTAGeneratorOutput

def generate_ctas(offer_details: dict, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are a Conversion Rate Optimization Expert.

Generate compelling Call-to-Actions (CTAs).

Offer Details:
{json.dumps(offer_details, indent=2)}

Return JSON only matching exactly this format:
{{
  "ctas": [
    {{
      "cta_text": "",
      "urgency_level": "High/Medium/Low",
      "clarity_score": 9.0
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
        output = CTAGeneratorOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"CTA Generator Error: {e}")
        return {"ctas": []}
