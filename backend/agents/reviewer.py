"""
Day 10 — Quality Reviewer (EVAL & REX Agents)
Models: llava (for vision), qwen3 (for text)
"""
import requests, json, base64
from config import settings
from schemas.agent_schemas import QualityReviewerOutput

def review_image(image_path: str, model_name: str = "llava") -> dict:
    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return {"error": "Image not found"}

    prompt = f"""Review this advertising image.

Score the following from 1 to 10:
- face_quality
- composition
- branding
- realism
- advertising_quality

Return JSON only matching exactly this format:
{{
  "face_quality": 8.0,
  "composition": 9.0,
  "branding": 7.5,
  "realism": 8.5,
  "advertising_quality": 8.0
}}"""

    r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
        "model": getattr(settings, "ollama_model_vision", model_name),
        "prompt": prompt,
        "images": [img_b64],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.3}
    }, timeout=120)

    try:
        raw = r.json().get("response", "")
        output = QualityReviewerOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Reviewer Error: {e}")
        return {
            "face_quality": 5.0,
            "composition": 5.0,
            "branding": 5.0,
            "realism": 5.0,
            "advertising_quality": 5.0
        }

def eval_asset(asset_type: str, asset_content: dict, strategy: dict, model_name: str = "qwen3") -> dict:
    """EVAL Agent: Scores generated assets against the Campaign Strategy."""
    prompt = f"""You are the EVAL Agent (Chief Quality Officer).
Evaluate this {asset_type} against the Campaign Strategy.

Campaign Strategy:
{json.dumps(strategy, indent=2)}

Asset Content ({asset_type}):
{json.dumps(asset_content, indent=2)}

Provide a score (1-10) and specific feedback for improvement.
Return JSON only:
{{
  "score": 8.5,
  "feedback": "Specific reasons for the score and actionable improvements."
}}"""
    try:
        r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
            "model": getattr(settings, "ollama_model", model_name),
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }, timeout=settings.ollama_request_timeout)
        return json.loads(r.json().get("response", ""))
    except Exception as e:
        print(f"EVAL Agent Error: {e}")
        return {"score": 5.0, "feedback": "Failed to evaluate."}


def rex_repair(asset_type: str, asset_content: dict, eval_feedback: str, strategy: dict, model_name: str = "qwen3") -> dict:
    """REX Agent: Intercepts low-scoring assets and forces repair/regeneration."""
    prompt = f"""You are the REX Agent (Repair Engine).
This {asset_type} failed quality control.

Campaign Strategy:
{json.dumps(strategy, indent=2)}

Current Weak {asset_type}:
{json.dumps(asset_content, indent=2)}

EVAL Feedback to fix:
"{eval_feedback}"

Rewrite and repair the asset to fully address the feedback and perfectly align with the strategy.
Return ONLY valid JSON matching the exact structure of the original {asset_type}.
"""
    try:
        r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
            "model": getattr(settings, "ollama_model", model_name),
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }, timeout=90)
        return json.loads(r.json().get("response", ""))
    except Exception as e:
        print(f"REX Agent Error: {e}")
        return asset_content # return original if repair fails
