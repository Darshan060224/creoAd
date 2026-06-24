"""
5. Multi-Round Review Agent
"""
import requests, json
from config import settings
from schemas.advanced_agent_schemas import MultiRoundReviewOutput

def review_campaign(content: dict, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are an Advertising Review Board.

Review generated content from:
Marketing Perspective
Creative Perspective
Brand Perspective
Visual Perspective

Content to Review:
{json.dumps(content, indent=2)}

Score each category from 1-10.

Identify:
weaknesses
strengths
improvement recommendations

Return JSON only matching exactly this format:
{{
  "marketing_score":0,
  "creative_score":0,
  "brand_score":0,
  "visual_score":0,
  "strengths":[],
  "weaknesses":[],
  "recommendations":[]
}}"""

    r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
        "model": getattr(settings, "ollama_model", model_name),
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.4}
    }, timeout=settings.ollama_request_timeout)

    try:
        raw = r.json().get("response", "")
        output = MultiRoundReviewOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Review Agent Error: {e}")
        return {
            "marketing_score": 0, "creative_score": 0, "brand_score": 0, "visual_score": 0,
            "strengths": [], "weaknesses": [], "recommendations": []
        }
