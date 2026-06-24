"""
Stage B1: Generate short ad script using Ollama (Llama 3.1 or Mistral)
"""

import requests
import json
import re
from typing import Dict, Any

try:
    from ..config import settings
    from ..pipeline.progress import pub_start, pub_log, pub_done, pub_error
except ImportError:
    from config import settings
    from pipeline.progress import pub_start, pub_log, pub_done, pub_error


def resolve_ollama_model() -> str:
    """Pick a model that is actually present in the live Ollama instance."""

    configured_model = settings.ollama_model.strip()
    preferred_models = [model.strip() for model in getattr(settings, "ollama_preferred_models", "").split(",") if model.strip()]

    try:
        response = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=10)
        response.raise_for_status()
        tags_payload = response.json()
        available_models = [model.get("name", "") for model in tags_payload.get("models", []) if model.get("name")]
    except Exception:
        return configured_model or (preferred_models[0] if preferred_models else "llama3.2:3b")

    candidate_models = [configured_model, *preferred_models]

    for model_name in candidate_models:
        if model_name and model_name in available_models:
            return model_name

    # Prefer small/fast models when available to reduce latency
    if available_models:
        for fast_model in ("phi3:mini", "llama3.2:3b", "phi4-mini", "mistral:7b-q4", "mistral:latest"):
            if fast_model in available_models:
                return fast_model
        return available_models[0]

    return configured_model or (preferred_models[0] if preferred_models else "llama3.2:3b")

def generate_ad_script(brand_data: Dict[str, Any], job_id: str = "unknown") -> Dict[str, Any]:
    """
    Use Ollama to generate a short 5-scene ad script
    """
    model_name = resolve_ollama_model()
    pub_start(job_id, "script", f"Ollama · {model_name}")
    import time
    start_time = time.time()
    
    prompt = build_script_prompt(brand_data)
    
    pub_log(job_id, "script", f"LLM Model: {model_name} · prompt={len(prompt)} chars", pct=5)
    company_name = brand_data.get('company_name') or brand_data.get('title') or 'unknown'
    pub_log(job_id, "script", f"LLM Brand: '{company_name}'", pct=8)
    pub_log(job_id, "script", f"LLM POST {settings.ollama_base_url}/api/generate", pct=10)
    
    try:
        r = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": settings.ollama_temperature,
                    "num_predict": getattr(settings, "ollama_num_predict", 4096),
                    "num_ctx": settings.ollama_num_ctx,
                    "num_gpu": 1 if getattr(settings, "ollama_gpu", True) else 0,
                    "stop": ["```", "---"],
                },
            },
            timeout=int(getattr(settings, "ollama_request_timeout", 60)),
            stream=True
        )
        r.raise_for_status()

        full_response = ""
        token_count = 0
        last_pub = 0

        pub_log(job_id, "script", "LLM Generating script tokens...", pct=15)

        for line in r.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
                token = chunk.get("response", "")
                full_response += token
                token_count += 1

                if token_count - last_pub >= 50:
                    last_pub = token_count
                    pct = min(15 + int(token_count / 6), 75)
                    pub_log(job_id, "script", f"LLM Streaming... {token_count} tokens generated", pct=pct)
                
                if chunk.get("done"):
                    break
            except json.JSONDecodeError:
                continue
        
        pub_log(job_id, "script", f"LLM Stream complete · {token_count} tokens · {time.time()-start_time:.1f}s", pct=80)
        
        script = parse_script_response(full_response)
        
        if script:
            headline = script.get('headline') or (script['scenes'][0].get('text', '') if script.get('scenes') else '')
            pub_log(job_id, "script", f"LLM ✓ Headline: \"{headline}\"", pct=90)
            pub_log(job_id, "script", f"LLM ✓ {len(script.get('scenes', []))} scenes", pct=95)
            pub_done(job_id, "script", time.time() - start_time)
            return script
            
        pub_log(job_id, "script", "LLM JSON parse failed — using fallback script", pct=85)

    except Exception as e:
        pub_log(job_id, "script", f"LLM ✗ Error: {str(e)[:100]} — using fallback", pct=50)

    # Fallback
    script = build_rule_based_script(brand_data)
    pub_log(job_id, "script", f"LLM Fallback script ready · {len(script.get('scenes', []))} scenes", pct=95)
    pub_done(job_id, "script", time.time() - start_time)
    return script

def build_script_prompt(brand_data: Dict[str, Any]) -> str:
    """Build the refined master prompt for Ollama.

    Uses a combined AIDA (Attention-Interest-Desire-Action) and PAS
    (Problem-Agitate-Solution) marketing framework mapped across
    exactly 5 scenes to maximise engagement and conversions.
    """

    company = brand_data.get('company_name', 'Business')
    description = brand_data.get('description', '')
    tagline = brand_data.get('tagline', '')
    products = brand_data.get('products', [])
    industry = brand_data.get('industry', 'services')
    cta = brand_data.get('call_to_action', 'Contact us today')
    tone = brand_data.get('tone', 'professional')

    products_text = ', '.join(products[:3]) if products else 'services'

    prompt = f"""You are an unparalleled, award-winning advertising creative director, a visionary storyboard artist, a master video editor, a persuasive copywriter, and a shrewd marketing strategist. Your expertise spans brand psychology, consumer behavior, cinematic storytelling, and technical video production.

Your task: create a hyper-optimised, 30-second commercial advertisement storyboard output as a single valid JSON object.

This storyboard will be consumed by an automated AI pipeline:
- ComfyUI + Stable Diffusion — photorealistic, cinematic image generation
- XTTS / Voice Engine — natural, emotive narration synthesis
- FFmpeg — video assembly with animations, transitions, and overlays
- Music Generator — background score composition
- SFX Engine — impactful sound effects

CORE MARKETING FRAMEWORK (AIDA + PAS) — map dynamically across your chosen number of scenes:
- Attention / Hook: Grab immediate attention, introduce the brand, hint at a core benefit.
- Problem / Interest: Articulate a common challenge the target audience faces, creating empathy.
- Agitate / Solution / Desire: Intensify the problem then reveal the brand as the definitive solution, building desire.
- Benefits / Social Proof: Showcase tangible benefits and positive outcomes with aspirational imagery.
- Action / CTA: Deliver a strong, unambiguous call to action and reinforce brand value.

STRICT JSON OUTPUT — return ONLY the JSON, no commentary:
{{
  "headline": "[Compelling, benefit-driven headline, < 100 chars]",
  "cta": "[Clear, actionable CTA with urgency, < 50 chars]",
  "music_style": "[Genre, mood, tempo, instrumentation — should evolve with emotional arc]",
  "video_style": "[Visual aesthetic, pacing, editing rhythm, color palette, lighting]",
  "brand_tone": "[2-3 adjectives + brief explanation of brand personality]",
  "total_duration": 30.0,
  "scenes": [
    {{
      "scene_number": 1,
      "duration": 6.0,
      "objective": "[Marketing objective for this scene]",
      "emotion": "[Primary emotion: Intrigue, Frustration, Hope, Joy, Urgency, etc.]",
      "narration": "[Concise, natural, persuasive narration — approx 15-17 words per scene, ~80 words total across all scenes]",
      "text_overlay": "[On-screen text, < 50 chars, complements narration without duplicating]",
      "transition": "[dissolve | fade | flash | wipeleft | wiperight | smoothzoom]",
      "sound_effect": "[whoosh | impact | click | pop | rise | swoosh | hit | sparkle | none]",
      "shots": [
        {{
          "duration": 3.0,
          "camera": "[zoom_in | zoom_out | pan_left | pan_right | push_in | pull_out | orbit_left | orbit_right | parallax]",
          "prompt": "[Extremely detailed cinematic image description for ComfyUI — subject, setting, lighting, composition, mood, color, textures. Include: cinematic lighting, commercial advertising photography, 8k, ultra detailed, depth of field, sharp focus]"
        }},
        {{
          "duration": 3.0,
          "camera": "[camera movement]",
          "prompt": "[Detailed cinematic image description]"
        }}
      ]
    }}
  ]
}}

CAMERA PSYCHOLOGY — choose deliberately:
- zoom_in: focus, intensity, importance
- zoom_out: revealing context, scale, grandeur
- pan_left / pan_right: breadth, progression, following action
- push_in / pull_out: emotional emphasis, dramatic tension / release
- orbit_left / orbit_right: dynamic perspective, energy
- parallax: depth, immersion, premium feel

RULES:
1. Choose the number of scenes dynamically based on pacing (e.g. 4 to 8 scenes). Sum of all scene durations MUST equal 30.0.
2. Choose the number of shots per scene dynamically based on the action (e.g. 1 to 5 shots per scene). Sum of shot durations MUST equal the scene duration.
3. Total narration across all scenes: approximately 75-85 words (suitable for 30s at natural pace).
4. Image prompts must be photorealistic, cinematic, commercial-grade. Describe lighting, composition, mood, colors, textures. Never cartoonish or illustrative.
5. Text overlays complement narration — never duplicate it. Under 50 characters.
6. Transitions and sound effects must match emotional and narrative flow. Use sound effects sparingly for maximum impact.
7. The entire output must be valid JSON. No text outside the JSON object.
8. Narration must feel natural, conversational, and authoritative — never robotic or overly salesy.
9. The story arc must flow logically and emotionally across all 5 scenes.
10. All creative choices must align with the brand data below.

BRAND DATA:
Product: {company}
Description: {description}
Tagline: {tagline}
Key Products/Services: {products_text}
Target Audience: Customers of {industry}
Brand Tone: {tone}
Goal: Generate leads and increase conversions
Video Length: 30 seconds
"""

    return prompt

def parse_script_response(raw_response: str) -> Dict[str, Any]:
    """Parse Ollama response and extract JSON

    Be tolerant of minor formatting issues by extracting the largest balanced JSON
    substring found in the reply. This reduces brittle failures when models return
    extra commentary or imperfectly-formatted JSON.
    """

    # Quick regex attempt first
    json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
    candidate = None

    if json_match:
        candidate = json_match.group(0)

    # If regex parse failed or produced invalid JSON, try to find a balanced JSON block
    if not candidate:
        # Find all balanced brace substrings and pick the longest
        starts = [i for i, ch in enumerate(raw_response) if ch == '{']
        best = None
        for s in starts:
            depth = 0
            for i in range(s, len(raw_response)):
                if raw_response[i] == '{':
                    depth += 1
                elif raw_response[i] == '}':
                    depth -= 1
                    if depth == 0:
                        cand = raw_response[s:i+1]
                        if not best or len(cand) > len(best):
                            best = cand
                        break
        candidate = best

    if not candidate:
        raise Exception("No JSON found in response")

    # Try to decode the candidate JSON; if it fails, raise a helpful error
    try:
        script = json.loads(candidate)
    except json.JSONDecodeError as e:
        # Attempt a small cleanup pass: remove trailing commas and control characters
        cleaned = re.sub(r",\s*\}", "}", candidate)
        cleaned = re.sub(r",\s*\]", "]", cleaned)
        try:
            script = json.loads(cleaned)
        except json.JSONDecodeError:
            raise Exception(f"Invalid JSON in response: {str(e)}")

    # Validate structure
    if 'scenes' not in script:
        raise Exception("Script must include scenes")

    scenes = list(script.get('scenes', []))
    if len(scenes) == 0:
        raise Exception("Script must include at least one scene")
    script['scenes'] = scenes
    
    # Ensure each scene has required fields
    for i, scene in enumerate(script['scenes']):
        scene['id'] = scene.get('scene_number', scene.get('id', i))
        scene['text'] = scene.get('text_overlay', scene.get('text', ''))
        scene['duration'] = scene.get('duration', 5)
        scene['transition'] = scene.get('transition', 'dissolve')
        scene['sound_effect'] = scene.get('sound_effect', 'whoosh')
        
        # Ensure shots array exists
        if 'shots' not in scene or not isinstance(scene['shots'], list) or len(scene['shots']) == 0:
            # Fallback: create a single shot using the scene's legacy image_prompt
            legacy_prompt = scene.get('image_prompt', scene.get('description', f"Scene {i+1} for {script.get('music_style', 'professional')} ad"))
            legacy_anim = scene.get('animation', 'zoom_in')
            scene['shots'] = [{
                'duration': scene['duration'],
                'camera': legacy_anim,
                'prompt': legacy_prompt
            }]
        
        # Ensure shots have valid fields
        for shot in scene['shots']:
            shot['duration'] = shot.get('duration', scene['duration'] / len(scene['shots']))
            shot['camera'] = shot.get('camera', 'zoom_in')
            shot['prompt'] = shot.get('prompt', f"Scene {i+1} visual")
    
    # Ensure narration exists
    if 'narration' not in script:
        # Reconstruct narration from scenes if not at root level
        scene_narrations = [s.get('narration', '') for s in script['scenes']]
        if any(scene_narrations):
            script['narration'] = ' '.join(scene_narrations)
        else:
            script['narration'] = f"Discover {script['scenes'][0].get('text', 'our services')}. {script.get('music_style', 'Professional solutions')}. Get started today."
    
    # Ensure music suggestion exists
    if 'music_suggestion' not in script:
        script['music_suggestion'] = script.get('music_style', "professional and modern")
    
    return script


def build_rule_based_script(brand_data: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic fallback script generator when Ollama is unavailable or returns invalid JSON.

    Generates a cinematic 5-scene storyboard following AIDA/PAS framework
    with 2 shots per scene and detailed image prompts.
    """
    company = brand_data.get('company_name') or brand_data.get('title') or 'Your Company'
    tagline = brand_data.get('tagline') or brand_data.get('slogan') or ''
    products = brand_data.get('products') or []
    industry = brand_data.get('industry') or brand_data.get('category') or 'services'
    cta = brand_data.get('call_to_action') or 'Learn more today'
    tone = brand_data.get('tone', 'professional')

    short_products = ', '.join(products[:2]) if products else 'our services'

    scenes = [
        {
            'id': 0, 'scene_number': 1, 'duration': 6.0,
            'objective': 'Grab attention and introduce the brand',
            'emotion': 'Intrigue',
            'narration': f'Introducing {company}. {tagline or "Innovation that drives results."}',
            'text_overlay': company[:40],
            'text': company[:40],
            'transition': 'dissolve',
            'sound_effect': 'whoosh',
            'shots': [
                {'duration': 3.0, 'camera': 'zoom_in',
                 'prompt': f'Cinematic close-up of {company} brand logo emerging from a dark, elegant background with soft volumetric lighting, premium glass-like reflections, shallow depth of field, commercial advertising photography, 8k, ultra detailed'},
                {'duration': 3.0, 'camera': 'pan_right',
                 'prompt': f'Wide establishing shot of a modern, sunlit workspace where diverse professionals use {short_products}, warm golden-hour lighting streaming through floor-to-ceiling windows, depth of field, commercial photography, 8k'}
            ]
        },
        {
            'id': 1, 'scene_number': 2, 'duration': 6.0,
            'objective': 'Present the problem the audience faces',
            'emotion': 'Frustration',
            'narration': f'Struggling with outdated {industry} solutions? You deserve better.',
            'text_overlay': 'Tired of This?',
            'text': 'Tired of This?',
            'transition': 'wipeleft',
            'sound_effect': 'impact',
            'shots': [
                {'duration': 3.0, 'camera': 'push_in',
                 'prompt': f'Close-up of a frustrated professional staring at a cluttered, disorganised desk with scattered papers and an outdated computer screen showing error messages, cold blue-grey lighting, dramatic shadows, cinematic mood, 8k, ultra detailed'},
                {'duration': 3.0, 'camera': 'pan_left',
                 'prompt': f'Medium shot of hands rubbing temples in frustration, blurred background of a chaotic office environment, shallow depth of field, moody desaturated color palette, commercial photography, 8k'}
            ]
        },
        {
            'id': 2, 'scene_number': 3, 'duration': 6.0,
            'objective': 'Reveal the brand as the solution',
            'emotion': 'Hope',
            'narration': f'{company} transforms your workflow with {short_products}. Simple, powerful, effective.',
            'text_overlay': 'Meet the Solution',
            'text': 'Meet the Solution',
            'transition': 'flash',
            'sound_effect': 'rise',
            'shots': [
                {'duration': 3.0, 'camera': 'zoom_out',
                 'prompt': f'Dramatic product reveal of {company} solution on a sleek, minimal surface with a bright, clean background transitioning from dark to light, volumetric god rays, pristine reflections, commercial product photography, 8k, ultra detailed, sharp focus'},
                {'duration': 3.0, 'camera': 'orbit_left',
                 'prompt': f'Over-the-shoulder shot of a confident professional using {short_products} on a modern device, clean UI visible on screen, warm optimistic lighting, bokeh background, commercial advertising photography, 8k'}
            ]
        },
        {
            'id': 3, 'scene_number': 4, 'duration': 6.0,
            'objective': 'Showcase benefits and social proof',
            'emotion': 'Joy',
            'narration': 'Faster results. Happier teams. Real impact you can measure.',
            'text_overlay': 'Fast. Reliable.',
            'text': 'Fast. Reliable.',
            'transition': 'smoothzoom',
            'sound_effect': 'sparkle',
            'shots': [
                {'duration': 3.0, 'camera': 'parallax',
                 'prompt': f'Split-screen montage of happy, diverse customers smiling while using the product in different settings — office, cafe, home — warm vibrant colors, golden lighting, depth of field, commercial lifestyle photography, 8k, ultra detailed'},
                {'duration': 3.0, 'camera': 'pan_right',
                 'prompt': 'Clean data dashboard showing upward-trending graphs and green success metrics on a premium monitor, soft ambient lighting, reflections on glass desk surface, professional tech photography, 8k, sharp focus'}
            ]
        },
        {
            'id': 4, 'scene_number': 5, 'duration': 6.0,
            'objective': 'Drive a clear call to action',
            'emotion': 'Urgency',
            'narration': f'{cta}. Start your journey with {company} today.',
            'text_overlay': cta[:40],
            'text': cta[:40],
            'transition': 'fade',
            'sound_effect': 'swoosh',
            'shots': [
                {'duration': 3.0, 'camera': 'push_in',
                 'prompt': f'Bold, vibrant call-to-action card featuring "{cta}" text prominently displayed against a dynamic gradient background in brand colors, {company} logo beneath, modern typography, cinematic lighting, 8k, ultra detailed'},
                {'duration': 3.0, 'camera': 'zoom_in',
                 'prompt': f'Final aspirational hero shot — confident person walking toward a bright future cityscape at golden hour, silhouette against warm sunlight, lens flare, volumetric lighting, cinematic depth of field, commercial photography, 8k'}
            ]
        }
    ]

    narration = ' '.join(s['narration'] for s in scenes)

    music_suggestion = 'upbeat, modern corporate pop with driving synth melodies and light percussion' if 'tech' in industry.lower() else 'warm, professional orchestral with subtle electronic elements'

    return {
        'headline': tagline[:100] if tagline else f'Discover {company} — {short_products}',
        'cta': cta,
        'music_style': music_suggestion,
        'video_style': 'Dynamic and polished with smooth transitions, warm color palette, cinematic lighting',
        'brand_tone': f'{tone.capitalize()}, Trustworthy, Empowering',
        'total_duration': 30.0,
        'scenes': scenes,
        'narration': narration,
        'music_suggestion': music_suggestion,
    }
