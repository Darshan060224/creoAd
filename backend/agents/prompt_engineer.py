"""
Day 9 — Prompt Engineer
"""
import requests, json
from config import settings
from schemas.agent_schemas import PromptEngineerOutput

def generate_prompt(shot_plan: dict, model_name: str = "qwen3") -> dict:
    prompt = f"""Convert shot plan into image prompts.

Include:
- camera
- lens
- lighting
- composition
- environment
- commercial quality

Shot Plan:
{json.dumps(shot_plan, indent=2)}

Return JSON only matching exactly this format:
{{
 "prompt":"..."
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
        output = PromptEngineerOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Prompt Engineer Error: {e}")
        return {"prompt": "Commercial quality, detailed, photorealistic"}
