"""
1. Brand DNA Memory Agent
"""
import requests, json
from config import settings
from schemas.advanced_agent_schemas import BrandDNAOutput

def extract_brand_dna(business_info: dict, model_name: str = "qwen3:32b") -> dict:
    prompt = f"""You are a Brand DNA Architect.

Your responsibility is to extract and maintain the permanent identity of a brand.

Analyze all available business information.

Business Information:
{json.dumps(business_info, indent=2)}

Extract:
brand_name
brand_voice
brand_personality
target_audience
visual_style
color_palette
emotional_positioning
communication_style
logo_usage_guidelines
photography_style
brand_values
unique_selling_points

Rules:
Never invent unsupported information.
Be consistent across campaigns.
Create reusable brand memory.

Return JSON only matching exactly this format:
{{
  "brand_name":"",
  "brand_voice":"",
  "brand_personality":"",
  "target_audience":"",
  "visual_style":"",
  "color_palette":[],
  "emotional_positioning":"",
  "communication_style":"",
  "logo_usage_guidelines":[],
  "photography_style":"",
  "brand_values":[],
  "unique_selling_points":[]
}}"""

    r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
        "model": getattr(settings, "ollama_model", model_name),
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.3}
    }, timeout=settings.ollama_request_timeout)

    try:
        raw = r.json().get("response", "")
        output = BrandDNAOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Brand DNA Agent Error: {e}")
        return {}
