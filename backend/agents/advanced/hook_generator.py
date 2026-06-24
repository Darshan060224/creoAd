"""
Phase 3 - Hook Generator
"""
import requests, json
from config import settings
from schemas.marketing_schemas import HookGeneratorOutput

def generate_hooks(brand_dna: dict, audience_data: dict, count: int = 50, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are a Master Direct Response Copywriter.
    
    First question: WHO IS THIS FOR?
    Generate {count} engaging hooks based on audience psychology.
    
    Brand DNA: {json.dumps(brand_dna, indent=2)}
    Audience Psychology: {json.dumps(audience_data, indent=2)}
    
    Rules for Hooks:
    1. Must target Pain, Desire, Fear, or Dream.
    2. Categories: Curiosity, Fear, Problem, Benefit, Story, Authority, Controversy, FOMO.
    3. Score each hook from 1-10 on Curiosity, Emotion, Clarity, and Urgency.
    4. Calculate 'overall_score' and ONLY return the top 3 hooks.
    
    Return JSON only matching exactly this format:
    {{
      "hooks": [
        {{
          "hook_text": "",
          "category": "",
          "emotion_triggered": "",
          "estimated_retention": 9.5,
          "score": 9.2
        }}
      ]
    }}"""

    r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
        "model": getattr(settings, "ollama_model", model_name),
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.8}
    }, timeout=120)

    try:
        raw = r.json().get("response", "")
        # Assuming HookGeneratorOutput can validate this
        output = HookGeneratorOutput.model_validate_json(raw)
        
        # In case the model returned more than 3, sort and slice
        hooks = output.model_dump().get("hooks", [])
        hooks = sorted(hooks, key=lambda x: x.get("score", 0), reverse=True)[:3]
        return {"hooks": hooks}
    except Exception as e:
        print(f"Hook Generator Error: {e}")
        return {"hooks": []}
