"""
Day 3 — Campaign Generator
Model: qwen3
"""
import requests, json
from config import settings
from schemas.agent_schemas import CampaignsListOutput

def generate_campaigns(brand_data: dict, model_name: str = "qwen3") -> dict:
    prompt = f"""You are a Master Campaign Strategist. 
Generate 4 highly specific advertising campaigns for this brand.
You MUST include exactly one of each of the following objectives:
1. Brand Awareness
2. Lead Generation
3. Retargeting
4. Seasonal Offer

For each campaign provide:
- campaign_name
- audience
- angle
- emotional_trigger
- objective (Must be one of the 4 listed above)

Brand Data:
{json.dumps(brand_data, indent=2)}

Return JSON only matching exactly this format:
{{
  "campaigns":[
    {{
      "campaign_name": "",
      "audience": "",
      "angle": "",
      "emotional_trigger": "",
      "objective": ""
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
        output = CampaignsListOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Campaign Generator Error: {e}")
        return {"campaigns": []}
