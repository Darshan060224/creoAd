"""
8. Marketing Intelligence Layer
"""
import requests, json
from config import settings
from schemas.advanced_agent_schemas import MarketingIntelligenceOutput

def analyze_market(business_data: dict, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are a Chief Marketing Strategist.

Analyze:
competitors
market positioning
customer desires
customer fears
industry trends
offer opportunities

Business Data:
{json.dumps(business_data, indent=2)}

Identify strategic opportunities.

Return JSON only matching exactly this format:
{{
  "market_position":"",
  "competitor_advantages":[],
  "competitor_weaknesses":[],
  "customer_desires":[],
  "customer_fears":[],
  "opportunities":[],
  "recommended_angle":""
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
        output = MarketingIntelligenceOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Marketing Intelligence Error: {e}")
        return {
            "market_position": "Unknown", "competitor_advantages": [],
            "competitor_weaknesses": [], "customer_desires": [],
            "customer_fears": [], "opportunities": [], "recommended_angle": "Trust"
        }
