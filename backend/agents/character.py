"""
Day 8 — Character Agent
"""
import requests, json
import uuid
from config import settings
from schemas.agent_schemas import CharacterOutput

def generate_character(brand_profile: dict, model_name: str = "qwen3", force_new: bool = False) -> dict:
    # Character Consistency Engine: check if we already have a character
    existing_characters = brand_profile.get("characters", [])
    if existing_characters and not force_new:
        print("Character Consistency Engine: Reusing existing character.")
        return existing_characters[0]

    prompt = f"""You are a Lead Casting Director.
Generate a consistent brand hero character (e.g. Hero_001) that matches this brand's tone.
This character will be used across multiple campaigns to build brand recognition.

Brand Profile:
{json.dumps(brand_profile, indent=2)}

Return JSON only matching exactly this format:
{{
 "character_id":"Hero_001",
 "gender":"",
 "age":"",
 "appearance":"Detailed facial and physical description",
 "clothing":"Typical wardrobe",
 "personality":""
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
        output = CharacterOutput.model_validate_json(raw)
        data = output.model_dump()
        if not data.get("character_id"):
            data["character_id"] = str(uuid.uuid4())
        return data
    except Exception as e:
        print(f"Character Agent Error: {e}")
        return {
            "character_id": str(uuid.uuid4()),
            "gender": "Any",
            "age": "30s",
            "appearance": "Professional",
            "clothing": "Business casual",
            "personality": "Friendly"
        }
