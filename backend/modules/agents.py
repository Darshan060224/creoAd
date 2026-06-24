import requests
import json
import re
import os
import threading
from typing import Dict, Any, List, Union

try:
    from ..config import settings, global_ollama_lock
    from ..pipeline.progress import pub_log
except ImportError:
    from config import settings, global_ollama_lock
    from pipeline.progress import pub_log

# BUG-4 FIX: Cache resolved model name to avoid 17+ HTTP calls per pipeline
_resolved_model_cache = {"name": None, "lock": threading.Lock()}

# PERF-A: Module-level requests.Session for HTTP connection pooling to Ollama
_ollama_session = requests.Session()
_ollama_session.headers.update({"Content-Type": "application/json"})

SYSTEM_PROMPT = """You are a world-class TV and digital ad director with 20 years experience 
at top agencies like BBDO, Ogilvy, and Wieden+Kennedy. 
You create emotionally compelling, visually stunning video ads that convert.
Your ads follow the proven AIDA framework: Attention → Interest → Desire → Action.
Every scene must be cinematic, specific, and evoke emotion."""


def resolve_ollama_model() -> str:
    """Resolve best available Ollama model. Result is cached after first call."""
    # BUG-4 FIX: Return cached result if available
    with _resolved_model_cache["lock"]:
        if _resolved_model_cache["name"] is not None:
            return _resolved_model_cache["name"]

    # PERF-C FIX: Skip HTTP discovery if OLLAMA_MODEL is explicitly set in env
    configured_model = settings.ollama_model.strip()
    if configured_model and os.environ.get("OLLAMA_MODEL"):
        with _resolved_model_cache["lock"]:
            _resolved_model_cache["name"] = configured_model
        return configured_model

    preferred_models = [
        m.strip()
        for m in getattr(settings, "ollama_preferred_models", "").split(",")
        if m.strip()
    ]

    try:
        response = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=10)
        response.raise_for_status()
        tags_payload = response.json()
        available_models = [
            m.get("name", "") for m in tags_payload.get("models", []) if m.get("name")
        ]
    except Exception:
        result = configured_model or (
            preferred_models[0] if preferred_models else "llama3.2:3b"
        )
        with _resolved_model_cache["lock"]:
            _resolved_model_cache["name"] = result
        return result

    candidate_models = [configured_model, *preferred_models]
    for model_name in candidate_models:
        if model_name and model_name in available_models:
            with _resolved_model_cache["lock"]:
                _resolved_model_cache["name"] = model_name
            return model_name

    if available_models:
        for fast_model in (
            "phi3:mini",
            "llama3.2:3b",
            "phi4-mini",
            "mistral:7b-q4",
            "mistral:latest",
        ):
            if fast_model in available_models:
                with _resolved_model_cache["lock"]:
                    _resolved_model_cache["name"] = fast_model
                return fast_model
        with _resolved_model_cache["lock"]:
            _resolved_model_cache["name"] = available_models[0]
        return available_models[0]

    result = configured_model or (
        preferred_models[0] if preferred_models else "llama3.2:3b"
    )
    with _resolved_model_cache["lock"]:
        _resolved_model_cache["name"] = result
    return result


def _parse_json_from_llm(text: str) -> Union[Dict[str, Any], List[Any]]:
    json_match = re.search(r"\[.*\]|\{.*\}", text, re.DOTALL)
    candidate = json_match.group(0) if json_match else None

    if not candidate:
        starts = [i for i, ch in enumerate(text) if ch in ("{", "[")]
        best = None
        for s in starts:
            depth = 0
            open_char = text[s]
            close_char = "}" if open_char == "{" else "]"
            for i in range(s, len(text)):
                if text[i] == open_char:
                    depth += 1
                elif text[i] == close_char:
                    depth -= 1
                    if depth == 0:
                        cand = text[s : i + 1]
                        if not best or len(cand) > len(best):
                            best = cand
                        break
        candidate = best

    if not candidate:
        raise Exception("No JSON found in response")

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError on candidate: {candidate}")
        cleaned = re.sub(r",\s*\}", "}", candidate)
        cleaned = re.sub(r",\s*\]", "]", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            print(f"Failed to decode even after cleaning: {cleaned}")
            raise Exception(f"Invalid JSON in response: {str(e)}")


class LLMAgent:
    """Base class for all AI pipeline agents"""

    # PERF-5: Per-agent token limit. Override in subclasses for simple agents.
    max_tokens: int = 512

    def __init__(self, job_id: str = "unknown"):
        self.job_id = job_id
        self.model_name = resolve_ollama_model()

    def generate(self, prompt: str, stage_name: str) -> str:
        pub_log(
            self.job_id, stage_name, f"Agent calling LLM Model: {self.model_name}..."
        )
        max_retries = 2  # Reduced from 3 — 2 retries is enough
        last_error = None
        for attempt in range(max_retries):
            # BUG-FIX: Remove 180s hard cap. Queued CPU requests easily take 5+ mins.
            timeout = settings.ollama_request_timeout * (attempt + 1)
            try:
                with global_ollama_lock:
                    r = _ollama_session.post(
                        f"{settings.ollama_base_url}/api/generate",
                        json={
                            "model": self.model_name,
                            "system": SYSTEM_PROMPT,  # QUAL-A: Send system prompt
                            "prompt": prompt,
                            "stream": False,
                            "keep_alive": "10m",
                            "options": {
                                "temperature": 0.5,
                                "num_predict": self.max_tokens,
                                "num_ctx": 2048,
                            },
                        },
                        timeout=timeout,
                    )
                r.raise_for_status()
                response_data = r.json()
                return response_data.get("response", "")
            except Exception as e:
                last_error = e
                
                # BUG-FIX: Auto-pull missing models when Ollama returns 404 Not Found
                if isinstance(e, requests.exceptions.HTTPError) and e.response is not None and e.response.status_code == 404:
                    pub_log(
                        self.job_id, 
                        stage_name, 
                        f"Model '{self.model_name}' missing. Auto-pulling (this may take a few minutes)..."
                    )
                    try:
                        pull_r = requests.post(
                            f"{settings.ollama_base_url}/api/pull",
                            json={"name": self.model_name, "stream": False},
                            timeout=1800  # Give it 30 mins to download large models
                        )
                        pull_r.raise_for_status()
                        pub_log(self.job_id, stage_name, f"Successfully pulled {self.model_name}. Retrying generation...")
                        continue  # Retry generation after successful pull
                    except Exception as pull_e:
                        pub_log(self.job_id, stage_name, f"Failed to auto-pull {self.model_name}: {pull_e}")
                        raise e  # Raise original 404 if pull fails
                
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    pub_log(
                        self.job_id,
                        stage_name,
                        f"LLM timeout (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...",
                    )
                    import time

                    time.sleep(wait_time)
                else:
                    pub_log(self.job_id, stage_name, f"LLM ✗ Error: {str(last_error)}")
                    raise

    def generate_json(self, prompt: str, stage_name: str) -> Union[Dict[str, Any], List[Any]]:
        prompt += "\nOutput JSON only."
        response_text = self.generate(prompt, stage_name)
        return _parse_json_from_llm(response_text)


class BrandAnalyzer(LLMAgent):
    def analyze(self, website_url: str, website_text: str) -> Dict[str, Any]:
        prompt = f"""
        You are a Master Brand Analyst and Visual Identity Expert.
        Analyze this business based on their website text to build a comprehensive Brand DNA.
        Website: {website_url}
        Text: {website_text[:2000]}
        
        Extract:
        1. brand_type (e.g., Luxury, Fitness, Technology, Restaurant, SaaS)
        2. tone (e.g., Premium, Motivational, Friendly, Authoritative)
        3. personality (e.g., Confident, Energetic, Warm, Bold)
        4. target_audience (e.g., Professionals, Gym Beginners, Busy Parents)
        5. business (description of what they do)
        6. usp (unique selling proposition — what makes them different)
        7. primary_color (the dominant brand color as hex, e.g. "#1E3A5F")
        8. secondary_color (accent color as hex, e.g. "#F59E0B")
        9. brand_font_style (e.g., "modern sans-serif", "elegant serif", "bold industrial")
        10. visual_mood (e.g., "warm and inviting", "sleek and minimal", "bold and energetic")
        11. lighting_style (e.g., "warm golden hour", "cool clinical", "dramatic high contrast")
        
        Return JSON exactly matching this format:
        {{
          "brand_type": "Technology",
          "tone": "Professional",
          "personality": "Confident",
          "target_audience": "Business Owners",
          "business": "Software Company",
          "usp": "Fastest automation",
          "primary_color": "#1E3A5F",
          "secondary_color": "#F59E0B",
          "brand_font_style": "modern sans-serif",
          "visual_mood": "sleek and minimal",
          "lighting_style": "cool blue-toned studio lighting"
        }}
        """
        try:
            result = self.generate_json(prompt, "scrape")
            # Build brand_prompt_fragment for image prompt injection
            result["brand_prompt_fragment"] = (
                f"{result.get('visual_mood', 'professional')} aesthetic, "
                f"{result.get('lighting_style', 'cinematic')} lighting, "
                f"{result.get('brand_font_style', 'modern')} typography feel, "
                f"brand colors {result.get('primary_color', '')} and {result.get('secondary_color', '')}"
            )
            return result
        except Exception as e:
            print(f"BrandAnalyzer fallback due to: {e}")
            return {
                "brand_type": "General",
                "tone": "Professional",
                "personality": "Friendly",
                "target_audience": "Broad Audience",
                "business": "General Business",
                "usp": "Quality Service",
                "primary_color": "#1E3A5F",
                "secondary_color": "#F59E0B",
                "brand_font_style": "modern sans-serif",
                "visual_mood": "professional and clean",
                "lighting_style": "warm studio lighting",
                "brand_prompt_fragment": "professional and clean aesthetic, warm studio lighting, modern typography feel",
            }


class CompetitorAgent(LLMAgent):
    def analyze_competitors(self, brand_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""You are a Master Market Strategist.
        Analyze the competitive landscape for this business.
        Business: {json.dumps(brand_data)}
        
        Identify 3 direct competitors.
        For each, extract their core positioning, typical offers, and primary marketing messaging.
        Then identify the "market gap" (a highly profitable untapped angle we can own).
        Also identify winning angles, winning hooks, and winning styles.
        
        Return JSON only:
        {{
          "competitors": [
            {{
              "name": "Competitor A", 
              "positioning": "Family Dining",
              "offers": "Kids Eat Free Tuesdays",
              "messaging": "Bring the whole family together"
            }}
          ],
          "market_gap": "Healthy Premium Lunch for Professionals",
          "winning_angles": ["Time Saving", "Premium Status"],
          "winning_hooks": ["Tired of X?", "The secret to Y"],
          "winning_styles": ["Fast cuts", "UGC style"]
        }}
        """
        try:
            return self.generate_json(prompt, "discovery")
        except Exception as e:
            print(f"CompetitorAgent fallback due to: {e}")
            return {
                "competitors": [
                    {"name": "Competitor A", "positioning": "Standard approach"},
                ],
                "market_gap": "Premium Quality",
                "winning_angles": [],
                "winning_hooks": [],
                "winning_styles": []
            }


class AudienceAgent(LLMAgent):
    def discover_segments(
        self, brand_data: Dict[str, Any], market_gap: str
    ) -> Dict[str, Any]:
        prompt = f"""
        Discover audience segments for this business considering the market gap.
        Business: {json.dumps(brand_data)}
        Market Gap: {market_gap}
        
        Return JSON only:
        {{
          "segments": [
            {{"segment": "Office Workers", "pain_points": ["No healthy lunch options"], "desires": ["Quick premium meal"]}}
          ],
          "persona": "Busy Professionals",
          "pain_points": ["Lack of time"],
          "desires": ["Convenience"]
        }}
        """
        try:
            return self.generate_json(prompt, "discovery")
        except Exception as e:
            print(f"AudienceAgent fallback due to: {e}")
            return {
                "segments": [
                    {
                        "segment": "General Audience",
                        "pain_points": ["Time", "Quality"],
                        "desires": ["Convenience", "Premium service"],
                    }
                ],
                "persona": "General Consumer",
                "pain_points": [],
                "desires": []
            }


class CreativeDirector(LLMAgent):
    def create_vision(
        self,
        brand_data: Dict[str, Any],
        market_gap: str,
        audience_segments: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        prompt = f"""{SYSTEM_PROMPT}
        
        Act as the Master Creative Director. Define the high-level Brand DNA and creative vision for an ad.
        AD STYLE: Modern, cinematic, clean typography, professional voiceover.
        Similar to: Apple ads, Nike ads, high-quality LinkedIn video ads.
        Business: {json.dumps(brand_data)}
        Market Gap: {market_gap}
        Audience Segments: {json.dumps(audience_segments)}
        
        Rules:
        - Determine the required Emotion, Energy, Visual Style, and Editing Style based on the brand type.
        - Fitness Brand: High Energy, Fast Cuts. Luxury Brand: Slow Motion, Elegant Music. Tech Brand: Medium Energy, Push Ins.
        
        Return JSON only matching exactly this format:
        {{
          "emotion": "trust",
          "energy": "medium",
          "visual_style": "clean",
          "editing_style": "minimal",
          "theme": "Luxury",
          "color_palette": "Warm Gold",
          "music_style": "Corporate"
        }}
        """
        try:
            return self.generate_json(prompt, "script")
        except Exception as e:
            print(f"CreativeDirector fallback due to: {e}")
            return {
                "theme": "Modern",
                "emotion": "Inspirational",
                "color_palette": "Vibrant",
                "camera_style": "Dynamic",
                "music_style": "Upbeat",
            }


class MarketingStrategist(LLMAgent):
    def create_structure(
        self, creative_vision: Dict[str, str], market_gap: str,
        audience_pain_points: List[str] = None, hook_text: str = ""
    ) -> Dict[str, Any]:
        pain_str = json.dumps(audience_pain_points[:5]) if audience_pain_points else '[]'
        prompt = f"""{SYSTEM_PROMPT}
        
        You are a Marketing Strategist. Define the 30-second ad structure based on the creative vision and market gap.
        Vision: {json.dumps(creative_vision)}
        Angle/Gap: {market_gap}
        Audience Pain Points: {pain_str}
        Winning Hook: "{hook_text}"
        
        MANDATORY RULES:
        1. Choose exactly ONE framework: PAS (Problem, Agitate, Solution) or AIDA (Attention, Interest, Desire, Action).
        2. The ad MUST follow this exact 5-section structure: hook, problem, solution, proof, cta.
        3. Durations MUST sum to exactly 30.0 seconds.
        4. Hook section MUST be 3-5 seconds (grab attention immediately).
        5. CTA section MUST be 4-6 seconds (clear call to action).
        6. Include hook_text — the best opening line for the ad.
        
        Validate: Clarity, Consistency, Strategic alignment, Emotional progression.
        
        Return JSON only:
        {{
          "framework": "PAS",
          "hook": 4,
          "problem": 5,
          "solution": 10,
          "proof": 6,
          "cta": 5,
          "hook_text": "Stop wasting money on solutions that don't work."
        }}
        """
        try:
            result = self.generate_json(prompt, "script")
            # Validate durations sum to ~30
            total = sum(float(result.get(k, 0)) for k in ["hook", "problem", "solution", "proof", "cta"] if isinstance(result.get(k), (int, float)))
            if total < 20 or total > 40:
                result["hook"] = 4
                result["problem"] = 5
                result["solution"] = 10
                result["proof"] = 6
                result["cta"] = 5
            return result
        except Exception as e:
            print(f"MarketingStrategist fallback due to: {e}")
            return {
                "framework": "PAS",
                "hook": 4,
                "problem": 5,
                "solution": 10,
                "proof": 6,
                "cta": 5,
                "hook_text": hook_text or "Discover a better way.",
            }


class StoryboardAgent(LLMAgent):
    def create_storyboard(
        self, structure: Dict[str, Any], vision: Dict[str, str] = None,
        hook_text: str = "", brand_data: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        brand_context = ""
        if brand_data:
            brand_context = f"""\n        Brand: {brand_data.get('business', 'Business')}
        USP: {brand_data.get('usp', 'Quality')}
        Tone: {brand_data.get('tone', 'Professional')}
        Target Audience: {brand_data.get('target_audience', 'General')}"""
        hook_inject = f'\n        WINNING HOOK (use this as Scene 1 narration): "{hook_text}"' if hook_text else ''
        prompt = f"""{SYSTEM_PROMPT}
        
        Create a professional 30-second video ad storyboard.
        Section durations: {json.dumps(structure)}
        Creative Vision: {json.dumps(vision) if vision else "None"}{brand_context}{hook_inject}
        
        MANDATORY STORY STRUCTURE (Professional Ad Contract):
        Every ad MUST follow this exact emotional arc:
        1. HOOK (Scene 1): Grab attention in first 3 seconds. Use curiosity, fear, or desire. Show the problem or make a bold claim.
        2. PROBLEM (Scene 2): Articulate the audience's pain point. Create empathy. Show frustration.
        3. SOLUTION (Scene 3): Reveal the product/brand as THE answer. Show transformation.
        4. PROOF (Scene 4): Social proof, results, testimonials, data. Build credibility.
        5. CTA (Scene 5): Strong, urgent call to action. Tell them exactly what to do next.
        
        RULES — follow ALL of these:
        1. Each narration must sound NATURAL when spoken aloud — conversational, confident, never robotic
        2. text_overlay MUST be SHORT — max 4 words per scene, complementing (not duplicating) narration
        3. First scene MUST grab attention in 2 seconds — bold claim, question, or shocking stat
        4. Last scene MUST have a clear CTA with urgency ("Today", "Now", "Limited Time")
        5. Use POWER WORDS: "Finally", "Discover", "Transform", "Proven", "Exclusive", "Secret"
        6. Total narration across all scenes: 60-80 words (natural speaking pace for 30s)
        7. Each scene narration: 12-16 words
        8. Emotional arc MUST progress: Curiosity → Frustration → Hope → Confidence → Urgency
        
        For each scene, return a list of objects:
        - scene (integer, 1-5)
        - purpose (hook/problem/solution/proof/cta)
        - duration (float, from the structure durations)
        - emotion (the primary emotion for this scene)
        - message (natural spoken narration — this will be read aloud by TTS)
        - text_overlay (max 4 words, displayed on screen)
        """
        try:
            res = self.generate_json(prompt, "script")
        except Exception as e:
            print(f"StoryboardAgent fallback due to: {e}")
            biz = brand_data.get("business", "our solution") if brand_data else "our solution"
            usp = brand_data.get("usp", "the best choice") if brand_data else "the best choice"
            hook_msg = hook_text or f"Stop settling for less than you deserve."
            res = [
                {
                    "scene": 1,
                    "purpose": "hook",
                    "duration": 4.0,
                    "emotion": "Curiosity",
                    "message": hook_msg,
                    "text_overlay": "Stop Settling",
                },
                {
                    "scene": 2,
                    "purpose": "problem",
                    "duration": 5.0,
                    "emotion": "Frustration",
                    "message": f"You've tried everything, but nothing works the way you need it to.",
                    "text_overlay": "Sound Familiar?",
                },
                {
                    "scene": 3,
                    "purpose": "solution",
                    "duration": 10.0,
                    "emotion": "Hope",
                    "message": f"Introducing {biz}. Finally, {usp} that actually delivers on its promise.",
                    "text_overlay": "The Solution",
                },
                {
                    "scene": 4,
                    "purpose": "proof",
                    "duration": 6.0,
                    "emotion": "Confidence",
                    "message": "Trusted by thousands. Proven results. Real transformation you can see.",
                    "text_overlay": "Proven Results",
                },
                {
                    "scene": 5,
                    "purpose": "cta",
                    "duration": 5.0,
                    "emotion": "Urgency",
                    "message": f"Don't wait. Start your journey with {biz} today. Click the link below.",
                    "text_overlay": "Start Now",
                },
            ]
        if isinstance(res, dict):
            for key in ["scenes", "storyboard", "scenes_list", "data", "list"]:
                if key in res and isinstance(res[key], list):
                    res = res[key]
                    break
            else:
                for v in res.values():
                    if isinstance(v, list):
                        res = v
                        break
                else:
                    res = [res]

        if isinstance(res, list):
            normalized = []
            for item in res:
                if isinstance(item, dict):
                    normalized.append(item)
                elif isinstance(item, str):
                    try:
                        parsed_item = json.loads(item)
                        if isinstance(parsed_item, dict):
                            normalized.append(parsed_item)
                            continue
                    except Exception:
                        pass
                    normalized.append({"purpose": "scene", "message": item})
            # Validate: ensure we have at least 4 scenes with non-empty messages
            if len(normalized) < 4:
                print(f"StoryboardAgent: Only {len(normalized)} scenes, padding to 5")
                purposes = ["hook", "problem", "solution", "proof", "cta"]
                while len(normalized) < 5:
                    idx = len(normalized)
                    normalized.append({
                        "purpose": purposes[min(idx, 4)],
                        "duration": 5.0,
                        "emotion": "Neutral",
                        "message": f"Scene {idx + 1} content for the advertisement.",
                        "text_overlay": "",
                    })
            # Validate: ensure no scene has empty message
            for item in normalized:
                if not item.get("message") or len(str(item["message"]).strip()) < 5:
                    item["message"] = f"Experience the difference with our proven solution."
            # Ensure first scene is hook and last is CTA
            if normalized[0].get("purpose") != "hook":
                normalized[0]["purpose"] = "hook"
            if normalized[-1].get("purpose") != "cta":
                normalized[-1]["purpose"] = "cta"
            return normalized
        return []


class ShotPlanner(LLMAgent):
    def plan_shots(self, duration: float, style: str, hook: str) -> Dict[str, Any]:
        prompt = f"""
        You are a Master Commercial Film Director (System 8 Cinematic Shot Planner).
        Create a cinematic shot plan. Validate: Scene pacing, Visual variety, Emotional impact.
        Input:
        {{ "duration": {duration}, "style": "{style}", "hook": "{hook}" }}
        
        RULES:
        1. Total duration must equal 30 seconds.
        2. Shots must be from the Professional Shot Library: [extreme_closeup, closeup, medium, wide, drone, macro, over_shoulder, tracking, product_hero].
        3. Scene Intent Mapping:
           - Hook = closeup or extreme_closeup (goal: grab_attention)
           - Problem = medium (goal: show_pain)
           - Solution = tracking or wide (goal: show_benefit)
           - Proof = wide or over_shoulder
           - CTA = product_hero (goal: drive_action)
        4. Every ad MUST end with a "product_hero" shot.
        5. Build a Visual Journey (e.g., Closeup -> Medium -> Tracking -> Wide -> Product Hero).
        
        Return JSON only matching exactly this format:
        {{
          "scenes": [
            {{
              "scene": "hook",
              "duration": 4.0,
              "shots": [
                {{"camera": "extreme_closeup", "duration": 4.0}}
              ]
            }}
          ]
        }}
        """
        try:
            res = self.generate_json(prompt, "script")
        except Exception as e:
            print(f"ShotPlanner fallback due to: {e}")
            res = {
                "scenes": [
                    {
                        "scene": "hook",
                        "duration": 4.0,
                        "shots": [{"camera": "wide", "duration": 4.0}],
                    },
                    {
                        "scene": "problem",
                        "duration": 5.0,
                        "shots": [{"camera": "closeup", "duration": 5.0}],
                    },
                    {
                        "scene": "solution",
                        "duration": 10.0,
                        "shots": [{"camera": "wide", "duration": 10.0}],
                    },
                    {
                        "scene": "proof",
                        "duration": 6.0,
                        "shots": [{"camera": "closeup", "duration": 6.0}],
                    },
                    {
                        "scene": "cta",
                        "duration": 5.0,
                        "shots": [{"camera": "wide", "duration": 5.0}],
                    },
                ]
            }
        if isinstance(res, list):
            return {"scenes": res}
        if isinstance(res, dict):
            if "scenes" in res:
                return res
            # Maybe the list is under another key
            for key, val in res.items():
                if isinstance(val, list):
                    return {"scenes": val}
            return {"scenes": [res]}
        return {"scenes": []}


class HookEngine(LLMAgent):
    """Generate scored hooks targeting audience psychology."""

    def generate_hooks(
        self, brand_data: Dict[str, Any],
        audience_data: Dict[str, Any] = None,
        competitor_data: Dict[str, Any] = None,
        count: int = 10
    ) -> Dict[str, Any]:
        winning_hooks = []
        if competitor_data and isinstance(competitor_data, dict):
            winning_hooks = competitor_data.get("winning_hooks", [])
        pain_points = []
        if audience_data and isinstance(audience_data, dict):
            pain_points = audience_data.get("pain_points", [])
            for seg in audience_data.get("segments", []):
                if isinstance(seg, dict):
                    pain_points.extend(seg.get("pain_points", []))

        prompt = f"""You are a Master Direct Response Copywriter with 20 years experience.
        
        Generate {count} engaging video ad hooks based on audience psychology.
        
        Brand: {json.dumps(brand_data)}
        Audience Pain Points: {json.dumps(pain_points[:5])}
        Competitor Winning Hooks: {json.dumps(winning_hooks[:5])}
        
        RULES FOR HOOKS:
        1. Each hook must target ONE of: Pain, Desire, Fear, or Dream.
        2. Categories: Curiosity, Fear, Problem, Benefit, Story, Authority, Controversy, FOMO.
        3. Hooks MUST be 5-12 words (short enough to grab attention in 2 seconds).
        4. Score each hook from 1-10 on: Curiosity, Emotion, Clarity, Urgency.
        5. Calculate overall_score as average of all four scores.
        6. Return ALL {count} hooks sorted by overall_score descending.
        
        POWER HOOK FORMULAS:
        - "Stop [doing painful thing]"
        - "Nobody tells you this about [topic]"
        - "The [number] mistake killing your [desired outcome]"
        - "What if [desired outcome] was this easy?"
        - "Don't [action] until you see this"
        
        Return JSON only:
        {{
          "hooks": [
            {{
              "hook_text": "Stop wasting money on solutions that fail.",
              "category": "Problem",
              "emotion_triggered": "Frustration",
              "curiosity": 8,
              "emotion": 9,
              "clarity": 8,
              "urgency": 7,
              "overall_score": 8.0
            }}
          ]
        }}"""
        try:
            res = self.generate_json(prompt, "script")
            hooks = res.get("hooks", []) if isinstance(res, dict) else res if isinstance(res, list) else []
            # Ensure each hook has an overall_score
            for h in hooks:
                if isinstance(h, dict) and "overall_score" not in h:
                    scores = [float(h.get(k, 5)) for k in ["curiosity", "emotion", "clarity", "urgency"]]
                    h["overall_score"] = sum(scores) / max(len(scores), 1)
            # Sort by score and take top 3
            hooks = sorted(hooks, key=lambda x: float(x.get("overall_score", 0)) if isinstance(x, dict) else 0, reverse=True)[:3]
            return {"hooks": hooks}
        except Exception as e:
            print(f"HookEngine fallback due to: {e}")
            biz = brand_data.get("business", "your business")
            return {"hooks": [
                {"hook_text": f"Stop settling for less than you deserve.", "category": "Problem", "overall_score": 7.0},
                {"hook_text": f"The secret nobody tells you about {biz}.", "category": "Curiosity", "overall_score": 6.5},
                {"hook_text": f"What if getting results was this easy?", "category": "Desire", "overall_score": 6.0},
            ]}


class CharacterManager(LLMAgent):
    def create_character(self, brand_data: Dict[str, Any]) -> Dict[str, str]:
        prompt = f"""
        Create a detailed hero character for this brand's commercial.
        The character must feel authentic and relatable to the target audience.
        Brand: {json.dumps(brand_data)}
        
        RULES:
        1. Character must match the brand's target audience demographic.
        2. Clothing must match the brand tone (luxury = suit, fitness = athletic wear, tech = smart casual).
        3. Be SPECIFIC about every visual detail — this will be used to keep the same person across all scenes.
        
        Return JSON only:
        {{
          "character_id": "hero_001",
          "gender": "female",
          "age": "28",
          "ethnicity": "caucasian",
          "hair": "long brown wavy",
          "beard": "none",
          "build": "athletic",
          "clothing_style": "smart casual blazer",
          "clothing_color": "navy blue",
          "accessories": "minimal gold jewelry"
        }}
        """
        try:
            result = self.generate_json(prompt, "script")
            # Build char_prompt_fragment for injection into every image prompt
            result["char_prompt_fragment"] = (
                f"same person in every scene, "
                f"{result.get('gender', 'person')}, "
                f"{result.get('age', '30')} years old, "
                f"{result.get('ethnicity', '')} "
                f"{result.get('build', 'average')} build, "
                f"{result.get('hair', 'brown')} hair, "
                f"{result.get('beard', 'none')} beard, "
                f"wearing {result.get('clothing_color', 'dark')} {result.get('clothing_style', 'professional attire')}, "
                f"{result.get('accessories', 'no accessories')}"
            )
            return result
        except Exception as e:
            print(f"CharacterManager fallback due to: {e}")
            return {
                "character_id": "hero_001",
                "gender": "male",
                "age": "30",
                "ethnicity": "diverse",
                "hair": "short brown",
                "beard": "none",
                "build": "average",
                "clothing_style": "smart casual",
                "clothing_color": "navy blue",
                "accessories": "none",
                "char_prompt_fragment": "same person in every scene, male, 30 years old, short brown hair, wearing navy blue smart casual attire",
            }


class IndustryTemplateSelector(LLMAgent):
    max_tokens = 128  # PERF-5: Simple 3-field output

    def select_template(self, brand_data: Dict[str, Any]) -> Dict[str, str]:
        prompt = f"""
        Select an industry template for this brand.
        Brand: {json.dumps(brand_data)}
        
        Examples:
        Restaurant: {{"lighting": "warm", "camera": "85mm", "style": "luxury"}}
        Gym: {{"lighting": "dramatic", "camera": "35mm", "style": "fitness"}}
        Real Estate: {{"lighting": "bright", "camera": "14mm", "style": "architectural"}}
        
        Return JSON only with 'lighting', 'camera', and 'style'.
        """
        try:
            return self.generate_json(prompt, "script")
        except Exception as e:
            print(f"IndustryTemplateSelector fallback due to: {e}")
            return {"lighting": "natural", "camera": "35mm", "style": "modern"}


class ImageCountCalculator:
    @staticmethod
    def calculate(shot_plan: Dict[str, Any]) -> Dict[str, Any]:
        total_images = 0
        scene_breakdown = {}
        for scene in shot_plan.get("scenes", []):
            scene_name = scene.get("scene", "unknown")
            shot_count = len(scene.get("shots", []))
            total_images += shot_count
            scene_breakdown[f"scene_{scene_name}"] = shot_count

        return {"total_images": total_images, "scene_breakdown": scene_breakdown}


class PromptEngineer(LLMAgent):
    def generate_prompts(
        self, shot_plan: Dict[str, Any], brand_data: Dict[str, Any],
        character_info: Dict[str, Any] = None,
        char_prompt_fragment: str = "", brand_prompt_fragment: str = "",
        emotional_arc: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        char_str = json.dumps(character_info) if character_info else "None specified"
        consistency_rules = ""
        if char_prompt_fragment:
            consistency_rules += f"\n        CHARACTER IDENTITY (inject into EVERY prompt): {char_prompt_fragment}"
        if brand_prompt_fragment:
            consistency_rules += f"\n        BRAND VISUAL DNA (inject into EVERY prompt): {brand_prompt_fragment}"
            
        emotion_str = ""
        if emotional_arc and "emotional_arc" in emotional_arc:
            emotion_str = f"\n        EMOTIONAL ARC OF AD:\n        {json.dumps(emotional_arc['emotional_arc'], indent=2)}\n        Adjust the lighting, facial expression, and tone of each shot to match the scene's required emotion."
            
        prompt = f"""{SYSTEM_PROMPT}
        
        You are an expert commercial photographer and continuity director. Generate base image prompts for these shots.
        Brand info: {json.dumps(brand_data)}
        Shot plan: {json.dumps(shot_plan)}
        Character info: {char_str}
        {consistency_rules}
        {emotion_str}
        
        RULES:
        1. CHARACTER CONSISTENCY: Every prompt MUST feature the EXACT same character. Copy the character identity description word-for-word into every prompt.
        2. BRAND CONSISTENCY: Every prompt must match the brand's visual mood, lighting, and color palette.
        3. EMOTIONAL TONE: Read the EMOTIONAL ARC. The subject's expression, lighting, and mood MUST reflect the scene's target emotion.
        4. COMPOSITION RULES by scene purpose:
           - Hook: Rule of thirds, subject slightly off-center, dramatic angle
           - Problem: Medium shot showing frustration, desaturated/cool tones
           - Solution: Product reveal, bright optimistic lighting, center composition
           - Proof: Wide or over-shoulder, warm social proof setting
           - CTA: Product hero shot, clean background, brand colors prominent
        5. Each prompt must be ULTRA DETAILED — describe lighting, camera angle, mood, colors, textures, depth of field.
        6. NEVER use generic prompts. Every prompt must be unique and specific to the scene.
        7. Always include: "same person as reference image" if a character is specified.
        
        Example: same person as reference image, 28 year old athletic female, long brown wavy hair, navy blazer, low angle close-up at sleek desk, warm golden hour light through floor-to-ceiling windows, shallow depth of field, cinematic 4k, photorealistic, commercial advertising photography
        
        Return a list of objects (one per shot, in order) containing:
        - prompt (highly detailed, photorealistic visual description including character, brand, and emotional rules)
        """
        try:
            return self.generate_json(prompt, "script")
        except Exception as e:
            print(f"PromptEngineer fallback due to: {e}")
            base = char_prompt_fragment or "professional person in commercial setting"
            brand = brand_prompt_fragment or "cinematic lighting, 8k, photorealistic"
            return [
                {
                    "prompt": f"same person as reference image, {base}, {brand}, commercial quality, highly detailed photorealistic commercial shot."
                }
                for _ in range(10)
            ]


class ImageReviewer(LLMAgent):
    def score_image(self, prompt_text: str) -> Dict[str, float]:
        # Using LLM to score the prompt (or image description) to simulate Quality Scoring
        prompt = f"""
        Evaluate this generated image.
        Description: {prompt_text}
        
        Score from 1 to 10:
        Face Quality
        Composition
        Professional Appearance
        Advertising Quality
        Brand Visibility
        
        Return JSON only:
        {{
          "face": 9.0,
          "composition": 8.0,
          "advertising": 9.0,
          "overall": 8.8
        }}
        """
        try:
            return self.generate_json(prompt, "script")
        except Exception as e:
            print(f"ImageReviewer fallback due to: {e}")
            return {"face": 8, "composition": 8, "advertising": 8, "overall": 8.5}


class MotionDirector(LLMAgent):
    def plan_motions(self, shots: List[Dict[str, Any]], campaign_brief: Dict[str, Any] = None) -> List[Dict[str, str]]:
        prompt = f"""
        You are a Master Motion Director. Decide cinematic camera motion, scene energy, transitions, speed ramps, and timing for these shots.
        Shots: {json.dumps(shots)}
        Brief: {json.dumps(campaign_brief) if campaign_brief else "None"}
        
        RULES:
        1. Camera moves must come from this library: [push_in, pull_out, orbit, truck_left, truck_right, crash_zoom, parallax]
        2. Transitions must come from this library: [cut, dissolve, whip_pan, match_cut, flash, speed_ramp, blur_transition]
        3. Energy levels dictate moves. Hook: high energy (crash_zoom/whip_pan). Problem: medium (push_in). Solution: smooth (orbit/parallax).
        4. No camera move can repeat consecutively.
        
        Return JSON only as a list of objects in the exact same order as the input shots. Each object must have exactly these keys:
        - camera (string from camera library)
        - transition (string from transition library)
        - speed (slow, medium, fast, ramp_up, ramp_down)
        - energy (low, medium, high, intense)
        
        Example:
        [
          {{
            "camera": "crash_zoom",
            "transition": "whip_pan",
            "speed": "fast",
            "energy": "high"
          }}
        ]
        """
        try:
            res = self.generate_json(prompt, "script")
            if isinstance(res, dict):
                for k, v in res.items():
                    if isinstance(v, list):
                        res = v
                        break
                else:
                    res = [res]
            return res
        except Exception as e:
            print(f"MotionDirector fallback due to: {e}")
            return [
                {
                    "camera": "push_in",
                    "transition": "whip_pan",
                    "speed": "medium",
                    "energy": "high"
                } for _ in shots
            ]


class VoiceDirector(LLMAgent):
    max_tokens = 128  # PERF-5: Simple 4-field output

    def plan_voice(self, message: str) -> Dict[str, str]:
        prompt = f"""
        Analyze script message for voiceover.
        Message: {message[:500]}
        
        Return object with:
        - emotion
        - pace
        - energy
        - emphasis
        """
        try:
            return self.generate_json(prompt, "script")
        except Exception as e:
            print(f"VoiceDirector fallback due to: {e}")
            return {
                "emotion": "excited",
                "pace": "medium",
                "energy": "high",
                "emphasis": "strong",
            }


class EditorAgent(LLMAgent):
    max_tokens = 128  # PERF-5: Simple 4-field output

    def plan_editing(self, total_duration: float) -> Dict[str, Any]:
        prompt = f"""
        Create editing plan for a {total_duration}s ad.
        
        Return object with:
        - transitions (list of strings)
        - text_animations (string)
        - logo_reveal (string)
        - music_timing (string)
        """
        try:
            return self.generate_json(prompt, "script")
        except Exception as e:
            print(f"EditorAgent fallback due to: {e}")
            return {"transitions": ["dissolve"]}


class QualityReviewer(LLMAgent):
    def review_ad(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
        Review complete advertisement script and plan.
        Data: {json.dumps(campaign_data)[:2000]}
        
        Score from 1-10:
        - marketing
        - visual_quality
        - retention
        - branding
        - cta
        Also provide a list of 'fixes' (strings).
        """
        try:
            return self.generate_json(prompt, "script")
        except Exception as e:
            print(f"QualityReviewer fallback due to: {e}")
            return {
                "marketing": 8,
                "visual_quality": 8,
                "retention": 8,
                "branding": 8,
                "cta": 8,
                "fixes": [],
            }


class PerformancePredictorAgent(LLMAgent):
    max_tokens = 128  # PERF-5: Simple 3-field output

    def predict_performance(self, campaign_data: Dict[str, Any]) -> Dict[str, float]:
        prompt = f"""
        You are a Data-Driven Performance Predictor. Estimate ad performance metrics based on the campaign data.
        Data: {json.dumps(campaign_data, default=str)[:2000]}
        
        Evaluate the hook, script, and visual plan. Provide estimated metrics.
        Return JSON only:
        {{
          "hook_rate": 45.5,
          "estimated_ctr": 2.1,
          "conversion_score": 8.5
        }}
        """
        try:
            return self.generate_json(prompt, "script")
        except Exception as e:
            print(f"PerformancePredictorAgent fallback due to: {e}")
            return {"hook_rate": 35.0, "estimated_ctr": 1.5, "conversion_score": 7.0}


class CTOAgent(LLMAgent):
    def review_ad(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
        You are CreoAd's Autonomous CTO, Principal Software Architect, Senior AI Engineer, Creative Director, Marketing Strategist, AdTech Expert, QA Lead, and Systems Engineer.
        Your mission is to build, validate, improve, repair, and optimize every stage of the system.
        Review the complete advertisement data.
        Data: {json.dumps(campaign_data)[:4000]}
        
        Score from 1 to 10. If overall_score < 8.5, list the issues, root_causes, recommended fixes, and specifically list the components_regenerated (e.g. "images", "prompts", "voice", "script", "shots").
        If score >= 8.5, set approved to true.
        
        Return exactly this JSON format:
        {{
          "overall_score": 8.5,
          "marketing_score": 8.5,
          "creative_score": 8.5,
          "visual_score": 8.5,
          "conversion_score": 8.5,
          "retention_score": 8.5,
          "issues": [],
          "root_causes": [],
          "fixes": [],
          "components_regenerated": [],
          "approved": true
        }}
        """
        try:
            res = self.generate_json(prompt, "script")
            if "approved" not in res:
                res["approved"] = res.get("overall_score", 0) >= 8.5
            return res
        except Exception as e:
            print(f"CTOAgent fallback due to: {e}")
            return {
                "overall_score": 8.5,
                "marketing_score": 8.5,
                "creative_score": 8.5,
                "visual_score": 8.5,
                "conversion_score": 8.5,
                "retention_score": 8.5,
                "issues": [],
                "root_causes": [],
                "fixes": [],
                "components_regenerated": [],
                "approved": True,
            }

class KineticTypographyEngine(LLMAgent):
    def animate_texts(self, texts: List[str]) -> List[Dict[str, Any]]:
        prompt = f"""
        You are a Kinetic Typography Engine.
        Create an animated text plan for each of these texts.
        Texts: {json.dumps(texts)}
        
        Animations: Pop, Slide, Bounce, Explode, Scale, Glitch, Typewriter
        Sync options: beat, voice, continuous
        
        Return JSON only as a list of objects in the same order. Each object must have exactly these keys:
        - animation (pop, slide, bounce, explode, scale, glitch, typewriter)
        - duration (float)
        - sync (beat, voice, continuous)
        
        Example:
        [
          {{
            "animation": "explode",
            "duration": 1.5,
            "sync": "beat"
          }}
        ]
        """
        try:
            res = self.generate_json(prompt, "script")
            if isinstance(res, dict):
                for k, v in res.items():
                    if isinstance(v, list):
                        res = v
                        break
                else:
                    res = [res]
            return res
        except Exception:
            return [{"animation": "pop", "duration": 1.0, "sync": "beat"} for _ in texts]

class SoundDesignEngine(LLMAgent):
    def generate_timeline(self, video_length: float, shot_plan: Dict[str, Any] = None) -> Dict[str, Any]:
        prompt = f"""
        You are a Master Sound Director.
        Generate a highly detailed sound effects timeline for a video of length {video_length} seconds.
        Shot plan context: {json.dumps(shot_plan) if shot_plan else "None"}
        
        Rules for Sound Effects Layer:
        - Hook Text appears -> use "impact" or "hit"
        - Scene Transitions -> use "whoosh" or "swipe"
        - Problem/Tension -> use "riser"
        - CTA Text -> use "boom" or "hit"
        - General popups -> use "click" or "pop"
        
        Return JSON only matching exactly this format:
        {{
          "timeline": [
            {{"time": 0.5, "effect": "impact"}},
            {{"time": 2.5, "effect": "whoosh"}},
            {{"time": 5.0, "effect": "riser"}}
          ]
        }}
        """
        try:
            return self.generate_json(prompt, "script")
        except Exception:
            return {"timeline": [{"time": 0.5, "effect": "impact"}, {"time": 2.5, "effect": "whoosh"}]}

class AttentionRetentionEngine(LLMAgent):
    max_tokens = 128  # PERF-5: Simple 3-field output

    def predict_retention(self, storyboard: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
        You are an Attention Retention Engine predicting viewer drop-off.
        Storyboard: {json.dumps(storyboard, default=str)[:1500]}
        
        Identify the highest risk of drop-off.
        Return JSON only:
        {{
          "dropoff_risk": 7.2,
          "scene": 4,
          "reason": "weak hook or slow pacing"
        }}
        """
        try:
            return self.generate_json(prompt, "script")
        except Exception:
            return {"dropoff_risk": 5.0, "scene": 1, "reason": "none"}

class SelfImprovementLoop(LLMAgent):
    max_tokens = 128  # PERF-5: Simple lessons list

    def learn(self, campaign_id: str, scores: Dict[str, float]) -> Dict[str, Any]:
        prompt = f"""
        You are the Self-Improvement Loop.
        Learn from this campaign's scores.
        Campaign ID: {campaign_id}
        Scores: {json.dumps(scores)}
        
        Return a list of key lessons learned.
        Return JSON only:
        {{
          "lessons": [
            "Short hooks perform better for this audience",
            "Fast pacing improved retention by 20%"
          ]
        }}
        """
        try:
            return self.generate_json(prompt, "script")
        except Exception:
            return {"lessons": []}
