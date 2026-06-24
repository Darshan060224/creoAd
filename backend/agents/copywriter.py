"""
Copywriter Agent
Input: brand_profile + creative_brief + duration
Output: ad script with AIDA framework, hooks, scenes
"""
import requests, json
from config import settings

FRAMEWORKS = {
    "AIDA": "Attention (hook) → Interest (problem) → Desire (solution+proof) → Action (CTA)",
    "PAS":  "Problem (pain) → Agitate (make it worse) → Solution (your product)",
    "BAB":  "Before (struggle) → After (transformation) → Bridge (how to get there)",
    "Story": "Character (relatable person) → Conflict (problem) → Resolution (your product)"
}

def write_script(brand_profile: dict, brief: dict, duration: int, job_id: str) -> dict:
    num_scenes = {15: 3, 30: 5, 60: 8}.get(duration, 5)
    scene_dur  = duration // num_scenes
    framework  = brief.get("ad_framework", "AIDA")
    framework_desc = FRAMEWORKS.get(framework, FRAMEWORKS["AIDA"])

    prompt = f"""You are a top advertising copywriter who has written ads for Apple, Nike, and Airbnb.

BRAND: {brand_profile.get('name')}
USP: {brand_profile.get('usp', '')}
TARGET AUDIENCE: {brand_profile.get('target_audience', '')}
PAIN POINT: {brand_profile.get('pain_point', '')}
TRANSFORMATION: {brand_profile.get('transformation', '')}

CREATIVE BRIEF:
Theme: {brief.get('theme')}
Emotion to trigger: {brief.get('emotion')}
Hook style: {brief.get('hook_style')}
Director note: {brief.get('director_note')}
Framework: {framework} — {framework_desc}

Write a {duration}-second video ad with {num_scenes} scenes of {scene_dur}s each.

RULES:
- headline: MAX 5 words, emotional and punchy
- narration: Natural spoken language. Warm. Human. NOT robotic.
- text_overlay: MAX 4 words. Bold. Impactful.
- visual_prompt: Ultra detailed. Camera angle + lighting + subject + mood + {brief.get('lighting')} lighting + {brief.get('visual_style')} style + {brief.get('color_palette', [''])[0]} color tones + photorealistic 4K
- First scene MUST use {brief.get('hook_style')} hook
- Last scene MUST include brand name + URL + CTA
- Use power words: Finally / Discover / Transform / Proven / Exclusive / You

Return ONLY valid JSON:
{{
  "headline": "5 word max",
  "hook": "opening 3-second text shown on screen",
  "scenes": [
    {{
      "id": 1,
      "duration": {scene_dur},
      "visual_prompt": "Ultra detailed cinematic scene description",
      "narration": "Natural spoken voiceover",
      "text_overlay": "Max 4 words",
      "emotion": "curiosity"
    }}
  ],
  "cta": "call to action max 6 words",
  "tone": "{brief.get('tone', 'professional')}",
  "music_mood": "{brief.get('music_mood', 'uplifting')}"
}}"""

    r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
        "model": getattr(settings, "ollama_model", "mistral:latest"),
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 900, "num_ctx": 3000, "temperature": 0.8}
    }, timeout=90)

    raw = r.json().get("response", "")
    raw = raw.replace("```json","").replace("```","").strip()
    s, e = raw.find("{"), raw.rfind("}")+1
    try:
        d = json.loads(raw[s:e])
        if d.get("scenes"):
            return d
    except Exception:
        pass

    return _fallback_script(brand_profile, duration, num_scenes, scene_dur)

def _fallback_script(brand, duration, num_scenes, scene_dur):
    name = brand.get('name', 'Brand')
    url  = brand.get('url', '')
    return {
        "headline": f"Discover {name} Today",
        "hook": "What if everything changed?",
        "scenes": [
            {"id":i+1,"duration":scene_dur,
             "visual_prompt":f"Cinematic professional scene {i+1} for {name} advertisement, 4K photorealistic",
             "narration":f"Scene {i+1} narration for {name}.",
             "text_overlay":f"{name}","emotion":"excitement"}
            for i in range(num_scenes)
        ],
        "cta": f"Visit {url}",
        "tone": "professional",
        "music_mood": "uplifting"
    }

def generate_hooks(brand_profile: dict, brief: dict, job_id: str) -> list:
    """Generate 5 hooks, score them, return top 3"""
    prompt = f"""Generate 5 powerful ad hooks for {brand_profile.get('name')}.
Hook type: {brief.get('hook_style', 'Bold statement')}
Audience: {brand_profile.get('target_audience', '')}
Pain point: {brand_profile.get('pain_point', '')}

Each hook must grab attention in 3 seconds.
Return JSON: {{"hooks": [{{"text":"...", "score":8, "why":"reason"}}]}}"""

    r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
        "model": getattr(settings, "ollama_model", "mistral:latest"),
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 400, "temperature": 0.9}
    }, timeout=45)

    raw = r.json().get("response", "")
    s, e = raw.find("{"), raw.rfind("}")+1
    try:
        data  = json.loads(raw[s:e])
        hooks = sorted(data.get("hooks",[]), key=lambda x: x.get("score",0), reverse=True)
        return hooks[:3]
    except Exception:
        return [{"text": brand_profile.get("tagline",""), "score": 5}]
