"""
3. Creative Brief Generator
"""
import requests, json
from config import settings
from schemas.advanced_agent_schemas import CreativeBriefOutput

def generate_creative_brief(business_info: dict, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are a Senior Creative Director.

Create a professional advertising brief.

Business Information:
{json.dumps(business_info, indent=2)}

Determine:
campaign objective
target audience
offer
key message
emotional goal
visual direction
marketing angle
call to action

Return JSON only matching exactly this format:
{{
  "objective":"",
  "target_audience":"",
  "offer":"",
  "key_message":"",
  "emotional_goal":"",
  "visual_direction":"",
  "marketing_angle":"",
  "cta":""
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
        output = CreativeBriefOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Creative Brief Generator Error: {e}")
        return {}
