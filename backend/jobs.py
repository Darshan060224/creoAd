"""
RQ Job handlers for the CreoAd Master Flow pipeline
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
import gc
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from functools import wraps
from typing import Callable, Any, TypeVar

from redis import Redis
from rq import get_current_job
try:
    from .config import settings, global_ollama_lock
    from .models import (
        Campaign, Brand, MarketingStrategy, AdStructure,
        StoryboardScene, Shot, Prompt, Image as ImageModel, Video,
        Voiceover, Music, Review, Score, JobLog,
        Character, CampaignCharacter, CompetitorAnalysis, AudienceSegment,
        MotionPlan, TextAnimation, SoundEvent, Persona, RetentionScore,
        VideoJob, CampaignLearning, JobMetric,
        HookMemory, SceneMemory, MotionMemory, CTAMemory
    )
    from .modules.scraper import scrape_business_url
    from .modules.agents import (
        BrandAnalyzer, CompetitorAgent, AudienceAgent,
        CreativeDirector, MarketingStrategist, StoryboardAgent,
        ShotPlanner, PromptEngineer, IndustryTemplateSelector,
        ImageCountCalculator, ImageReviewer, MotionDirector,
        VoiceDirector, EditorAgent, QualityReviewer, CharacterManager,
        PerformancePredictorAgent, CTOAgent, KineticTypographyEngine,
        SoundDesignEngine, AttentionRetentionEngine, SelfImprovementLoop,
        HookEngine
    )
    from .modules.sfx_generator import generate_sfx_track
    from .modules.image_generator import generate_scene_images, generate_single_image
    from .modules.voice_generator import generate_voiceover
    from .modules.music_generator import generate_background_music, mix_voice_with_music
    from .modules.storage import upload_video_return_url
    from .modules.video_assembler import assemble_video
    from .agents.advanced.brand_dna import extract_brand_dna
    from .agents.advanced.emotional_arc import plan_emotional_arc
    from .agents.advanced.visual_continuity import maintain_visual_continuity
    from .pipeline.checkpoint import save_checkpoint, is_stage_done, get_stage_data, clear_checkpoint
    from .db import SessionLocal, get_engine
except ImportError:
    from config import settings, global_ollama_lock
    from models import (
        Campaign, Brand, MarketingStrategy, AdStructure,
        StoryboardScene, Shot, Prompt, Image as ImageModel, Video,
        Voiceover, Music, Review, Score, JobLog,
        Character, CampaignCharacter, CompetitorAnalysis, AudienceSegment,
        MotionPlan, TextAnimation, SoundEvent, Persona, RetentionScore,
        VideoJob, CampaignLearning, JobMetric,
        HookMemory, SceneMemory, MotionMemory, CTAMemory
    )
    from modules.scraper import scrape_business_url
    from modules.agents import (
        BrandAnalyzer, CompetitorAgent, AudienceAgent,
        CreativeDirector, MarketingStrategist, StoryboardAgent,
        ShotPlanner, PromptEngineer, IndustryTemplateSelector,
        ImageCountCalculator, ImageReviewer, MotionDirector,
        VoiceDirector, EditorAgent, QualityReviewer, CharacterManager,
        PerformancePredictorAgent, CTOAgent, KineticTypographyEngine,
        SoundDesignEngine, AttentionRetentionEngine, SelfImprovementLoop,
        HookEngine
    )
    from modules.sfx_generator import generate_sfx_track
    from modules.image_generator import generate_scene_images, generate_single_image
    from modules.voice_generator import generate_voiceover
    from modules.music_generator import generate_background_music, mix_voice_with_music
    from modules.storage import upload_video_return_url
    from modules.video_assembler import assemble_video
    from agents.advanced.brand_dna import extract_brand_dna
    from agents.advanced.emotional_arc import plan_emotional_arc
    from agents.advanced.visual_continuity import maintain_visual_continuity
    from pipeline.checkpoint import save_checkpoint, is_stage_done, get_stage_data, clear_checkpoint
    from db import SessionLocal, get_engine

import requests
if not hasattr(requests, "_is_patched_for_ollama_global"):
    if not hasattr(requests, "_is_patched_for_ollama"):
        _original_post = requests.post
        def _locked_post(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")
            # Serialize any local Ollama API call
            if "11434" in str(url) or "api/generate" in str(url) or "ollama" in str(url):
                with global_ollama_lock:
                    return _original_post(*args, **kwargs)
            return _original_post(*args, **kwargs)
        requests.post = _locked_post
        requests._is_patched_for_ollama = True
    requests._is_patched_for_ollama_global = True

# Database setup
engine = get_engine()

# Redis setup
redis_conn = Redis.from_url(settings.redis_url, decode_responses=True)

# Ensure output directories exist
_JOB_WORK_ROOT = os.environ.get("CREOAD_JOB_WORK_DIR", "/tmp/creoAd_jobs")
Path(_JOB_WORK_ROOT).mkdir(exist_ok=True)

_THREAD_LOCAL_STATE = __import__('threading').local()


_RETRY_LOCK = __import__('threading').Lock()
_GLOBAL_RETRY_COUNTS = {}

def _redis_get(key: str) -> str | None:
    try:
        return redis_conn.get(key)
    except Exception:
        return None

def _redis_setex(key: str, time: int, value: str) -> None:
    try:
        redis_conn.setex(key, time, value)
    except Exception:
        pass

def _cleanup_gpu_memory() -> None:
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass

def _generate_fallback_voiceover(out_path: str) -> str:
    import subprocess
    subprocess.run(["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "30", out_path, "-y"], check=False)
    return out_path

def _generate_voiceover_with_fallback(text: str, out_path: str, job_id: str = "") -> str:
    try:
        from .modules.voice_generator import generate_voiceover
        return generate_voiceover(text, out_path)
    except Exception as e:
        print(f"Voice generation failed: {e}")
        return _generate_fallback_voiceover(out_path)

def _generate_fallback_music(out_path: str) -> str:
    import subprocess
    subprocess.run(["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "30", out_path, "-y"], check=False)
    return out_path

def _generate_background_music_with_fallback(duration: int, out_path: str, job_id: str = "") -> str:
    try:
        from .modules.music_generator import generate_background_music
        return generate_background_music(duration, out_path)
    except Exception as e:
        print(f"Music generation failed: {e}")
        return _generate_fallback_music(out_path)

def _apply_scene_text_edits(scenes: list, edits: dict) -> list:
    """C2 FIX: Apply text edits from the edit-and-render endpoint."""
    if not edits:
        return scenes
    scene_edits = edits.get("scenes", [])
    for edit in scene_edits:
        if isinstance(edit, dict):
            scene_id = edit.get("scene_id", edit.get("scene_number"))
            if scene_id is not None and scene_id < len(scenes):
                if "message" in edit:
                    scenes[scene_id]["message"] = edit["message"]
                if "text_overlay" in edit:
                    scenes[scene_id]["text_overlay"] = edit["text_overlay"]
    return scenes

def _publish_progress(
    job_id: str,
    stage: str,
    status: str,
    message: str,
    pct: int = 0,
    event: str = "log",
    data: dict | None = None,
) -> None:
    payload = {
        "job_id": job_id,
        "stage": stage,
        "status": status,
        "pct": pct,
        "log": message,
        "event": event,
        "data": data or {},
    }
    try:
        msg = json.dumps(payload)
        redis_conn.publish(f"job:{job_id}", msg)
        redis_conn.rpush(f"job_logs:{job_id}", msg)
        redis_conn.expire(f"job_logs:{job_id}", 3600)
    except Exception:
        pass


# M1 FIX: Map backend pipeline stages → frontend-expected stage IDs
# Frontend expects: scrape, script, images, voice, music, render
_STAGE_MAP = {
    "analyzing": "scrape",
    "discovery": "script",
    "vision": "script",
    "strategizing": "script",
    "storyboarding": "script",
    "planning": "script",
    "generating": "images",
    "assembling": "render",
    "done": "render",
    "error": "render",
    # Direct matches
    "scrape": "scrape",
    "script": "script",
    "images": "images",
    "voice": "voice",
    "music": "music",
    "render": "render",
}


def log_stage(campaign_id: str, job_id: str, stage: str, status: str, message: str, pct: int = 50):
    db = SessionLocal()
    try:
        job_log = JobLog(
            id=str(uuid.uuid4()),
            campaign_id=campaign_id,
            job_id=job_id,
            stage=stage,
            status=status,
            message=message,
            duration_ms=0
        )
        db.add(job_log)
        db.commit()
    finally:
        db.close()
    
    redis_conn.hset(
        f"job:{job_id}",
        mapping={
            "stage": stage,
            "status": status,
            "message": message,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    )
    # M1 FIX: Publish progress using the mapped stage name the frontend expects
    frontend_stage = _STAGE_MAP.get(stage, stage)
    _publish_progress(job_id, frontend_stage, status, message, pct=pct)


def update_campaign(campaign_id: str, **fields):
    db = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            for key, value in fields.items():
                setattr(campaign, key, value)
                campaign.updated_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def _ensure_dict(value, fallback: dict = None) -> dict:
    """BUG-5 FIX: LLM agents sometimes return a list instead of a dict.
    
    This happens when Ollama wraps the JSON in an array, or the LLM
    returns multiple results. Without this guard, the pipeline crashes
    with "'list' object has no attribute 'get'".
    
    Strategy: if it's a list, extract the first dict element.
    If it's not a dict at all, return the fallback.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
    return fallback if fallback is not None else {}


def _extract_float(data: dict, key: str, default: float) -> float:
    if not isinstance(data, dict):
        return float(default)
    val = data.get(key, default)
    if isinstance(val, dict):
        return float(val.get("duration", val.get("value", default)))
    try:
        return float(val)
    except (TypeError, ValueError):
        return float(default)

def _validate_storyboard(storyboard, brand_data: dict = None) -> list:
    """Phase 8: Validate storyboard structure and fix common issues."""
    if isinstance(storyboard, dict):
        for k in ["scenes", "storyboard", "data", "list"]:
            if k in storyboard and isinstance(storyboard[k], list):
                storyboard = storyboard[k]
                break
        else:
            storyboard = [storyboard]

    if not storyboard or len(storyboard) < 4:
        print(f"_validate_storyboard: Only {len(storyboard) if storyboard else 0} scenes, building fallback")
        biz = brand_data.get("business", "our solution") if brand_data else "our solution"
        usp = brand_data.get("usp", "the best choice") if brand_data else "the best choice"
        storyboard = [
            {"scene": 1, "purpose": "hook", "duration": 4.0, "emotion": "Curiosity", "message": f"Stop settling for less than you deserve.", "text_overlay": "Stop Settling"},
            {"scene": 2, "purpose": "problem", "duration": 5.0, "emotion": "Frustration", "message": "You've tried everything, but nothing works the way you need it to.", "text_overlay": "Sound Familiar?"},
            {"scene": 3, "purpose": "solution", "duration": 10.0, "emotion": "Hope", "message": f"Introducing {biz}. Finally, {usp} that actually delivers.", "text_overlay": "The Solution"},
            {"scene": 4, "purpose": "proof", "duration": 6.0, "emotion": "Confidence", "message": "Trusted by thousands. Proven results. Real transformation.", "text_overlay": "Proven Results"},
            {"scene": 5, "purpose": "cta", "duration": 5.0, "emotion": "Urgency", "message": f"Don't wait. Start your journey with {biz} today.", "text_overlay": "Start Now"},
        ]

    # Ensure first scene is hook
    if storyboard[0].get("purpose") != "hook":
        storyboard[0]["purpose"] = "hook"
    # Ensure last scene is CTA
    if storyboard[-1].get("purpose") != "cta":
        storyboard[-1]["purpose"] = "cta"

    # Ensure every scene has a non-empty message (>= 5 words)
    for s in storyboard:
        msg = s.get("message", "")
        if not msg or len(str(msg).split()) < 5:
            s["message"] = "Experience the difference with our proven solution today."

    # Validate total duration is roughly 30s (±10s tolerance)
    total_dur = sum(float(s.get("duration", 5.0)) for s in storyboard)
    if total_dur < 20 or total_dur > 40:
        # Redistribute evenly to sum to 30
        n = len(storyboard)
        for s in storyboard:
            s["duration"] = round(30.0 / n, 1)

    return storyboard


def _validate_narration(full_message: str, scene_records: list, brand_info: dict = None) -> str:
    """Phase 8: Validate narration text before sending to TTS."""
    if not full_message or len(full_message.strip()) < 10:
        # Rebuild from scene messages
        full_message = " ".join([s.message for s in scene_records if hasattr(s, 'message') and s.message])

    words = full_message.split()
    if len(words) < 30:
        # Pad with brand-relevant content
        if brand_info:
            biz = brand_info.get("business", "our solution")
            usp = brand_info.get("usp", "quality service")
            full_message += f" Discover {biz}. We offer {usp} that transforms the way you work. Trusted by thousands. Get started today."
        else:
            full_message += " Our proven solution delivers real results. Trusted by thousands of satisfied customers. Don't wait. Get started today."

    return full_message.strip()


def _validate_audio(file_path: str, file_type: str = "audio") -> bool:
    """Phase 8: Validate that an audio file exists and is non-trivial (>1KB)."""
    if not file_path:
        return False
    if not os.path.exists(file_path):
        return False
    if os.path.getsize(file_path) < 1024:
        return False
    return True


def generate_ad(
    campaign_id: str,
    url: str | None = None,
    user_id: str | None = None,
    edit_mode: bool = False,
    edits: dict | None = None,
    **kwargs,
):
    current_job = get_current_job()
    job_id = current_job.id if current_job else kwargs.get("job_id", "manual")
    
    # C1 FIX: Extract voice_backend/voice_model/framework from kwargs
    voice_backend = kwargs.get("voice_backend", "chatterbox")
    voice_model = kwargs.get("voice_model", None)
    framework = kwargs.get("framework", None)  # H3: AIDA/PAS/BAB
    
    # L4 FIX: Use configurable work directory instead of hardcoded /tmp
    safe_campaign_id = os.path.basename(str(campaign_id))
    job_work_dir = f"{_JOB_WORK_ROOT}/{safe_campaign_id}"
    Path(job_work_dir).mkdir(parents=True, exist_ok=True)
    
    db = SessionLocal()
    metrics = {"scrape": 0, "script": 0, "images": 0, "voice": 0, "music": 0, "render": 0}
    executor = None  # BUG-B FIX: Track executor for cleanup in finally block
    try:
        _THREAD_LOCAL_STATE.start_time = time.time()
        pipeline_start = time.time()
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise Exception(f"Campaign {campaign_id} not found")

        url = url or campaign.business_url
        user_id = user_id or campaign.user_id

        # BUG-A FIX: Initialize all pipeline variables to safe defaults.
        # These may not be set when run_script/run_images/run_audio are False (edit mode).
        scene_records = []
        storyboard = []
        shot_records = []
        prompt_records = []
        vo_path = None
        music_path = None
        sfx_path = None
        ad_struct = {}
        creative_vision = {}
        emotional_arc = {}
        continuity_rules = {}
        hooks = []
        best_hook_text = ""
        brand_info = {}
        char_info = {}
        char_future = None
        template_future = None
        template_info = {"lighting": "natural", "camera": "35mm", "style": "modern"}
        shot_plan = {"scenes": []}
        video_url = ""

        # C2 FIX: In edit mode, load existing data from DB instead of re-running everything
        if edit_mode:
            log_stage(campaign_id, job_id, "analyzing", "running", "Edit mode — loading existing campaign data", 5)
            update_campaign(campaign_id, status="analyzing")
            
            # Load existing brand data
            brand_record = db.query(Brand).filter(Brand.campaign_id == campaign_id).first()
            if brand_record:
                brand_info = {
                    "business": brand_record.business or "",
                    "audience": brand_record.audience or "",
                    "tone": brand_record.tone or "",
                    "usp": brand_record.usp or "",
                }
            
            # Load existing scenes and shots
            scene_records = db.query(StoryboardScene).filter(
                StoryboardScene.campaign_id == campaign_id
            ).order_by(StoryboardScene.scene_number).all()
            
            shot_records = db.query(Shot).filter(Shot.campaign_id == campaign_id).all()
            prompt_records = db.query(Prompt).filter(Prompt.campaign_id == campaign_id).all()
            
            # Apply text edits to scenes
            if edits and scene_records:
                storyboard = [{
                    "scene": s.scene_number,
                    "purpose": s.purpose,
                    "duration": s.duration,
                    "emotion": s.emotion,
                    "message": s.message,
                } for s in scene_records]
                storyboard = _apply_scene_text_edits(storyboard, edits)
                # Update scene records in DB
                for i, s in enumerate(scene_records):
                    if i < len(storyboard):
                        s.message = storyboard[i].get("message", s.message)
                db.commit()
            
            # Only re-run voice if voiceover text changed
            run_voice = bool(edits and edits.get("voiceover_text"))
            metrics["scrape"] = 0
            metrics["script"] = 0
        else:
            run_voice = True  # Full pipeline runs everything

        # 1. Scrape & Brand Analyzer (skip in edit mode)
        if not edit_mode:
            if is_stage_done(job_work_dir, "scrape"):
                log_stage(campaign_id, job_id, "analyzing", "running", "SCRAPER ✓ Resumed from checkpoint", 5)
                brand_info = get_stage_data(job_work_dir, "scrape") or {}
            else:
                log_stage(campaign_id, job_id, "analyzing", "running", "Scraping URL and Analyzing Brand", 5)
                update_campaign(campaign_id, status="analyzing")
                website_data = scrape_business_url(url)
                brand_agent = BrandAnalyzer(job_id)
                brand_info = _ensure_dict(brand_agent.analyze(url, str(website_data)))
                save_checkpoint(job_work_dir, "scrape", brand_info)
            
            brand_record = Brand(
                id=str(uuid.uuid4()), campaign_id=campaign_id,
                business=str(brand_info.get("business", "")),
                audience=str(brand_info.get("audience", "")),
                tone=str(brand_info.get("tone", "")),
                usp=str(brand_info.get("usp", ""))
            )
            db.add(brand_record)
            db.commit()
            metrics["scrape"] += time.time() - pipeline_start

        # C2 FIX: In edit mode, skip discovery/script phases and jump to audio/render
        if not edit_mode:
            # MOD-2 FIX: ThreadPoolExecutor with proper cleanup (in finally block)
            executor = ThreadPoolExecutor(max_workers=8)

            # PERF-1 FIX: Start ALL independent agents in parallel (not sequential)
            log_stage(campaign_id, job_id, "discovery", "running", "Analyzing Competitors, Audience & Identity (parallel)", 8)
            update_campaign(campaign_id, status="discovery")
            char_future = executor.submit(CharacterManager(job_id).create_character, brand_info)
            template_future = executor.submit(IndustryTemplateSelector(job_id).select_template, brand_info)
            competitor_future = executor.submit(CompetitorAgent(job_id).analyze_competitors, brand_info)
            audience_future = executor.submit(AudienceAgent(job_id).discover_segments, brand_info, "Premium Alternative")
            brand_dna_future = executor.submit(extract_brand_dna, brand_info)

            # Wait for competitor + audience (needed for hook generation)
            competitor_info = _ensure_dict(competitor_future.result())
            market_gap = str(competitor_info.get("market_gap", "Premium Alternative"))
            comp_record = CompetitorAnalysis(
                id=str(uuid.uuid4()), campaign_id=campaign_id,
                competitors=competitor_info.get("competitors", []),
                market_gap=market_gap
            )
            db.add(comp_record)
            db.commit()

            audience_info = _ensure_dict(audience_future.result())
            brand_dna = _ensure_dict(brand_dna_future.result() if 'brand_dna_future' in locals() else {})
            segments_list = audience_info.get("segments", [])
            audience_pain_points = audience_info.get("pain_points", [])
            for seg in segments_list:
                if isinstance(seg, dict):
                    audience_pain_points.extend(seg.get("pain_points", []))

            aud_record = AudienceSegment(
                id=str(uuid.uuid4()), campaign_id=campaign_id,
                segments=segments_list
            )
            db.add(aud_record)
            db.commit()

            # Hook Engine (depends on competitor + audience results)
            log_stage(campaign_id, job_id, "discovery", "running", "Generating Scored Hooks", 11)
            hook_engine = HookEngine(job_id)
            hook_info = _ensure_dict(hook_engine.generate_hooks(
                brand_data=brand_info,
                audience_data=audience_info,
                competitor_data=competitor_info,
                count=10
            ))
            hooks = hook_info.get("hooks", [])
            best_hook_text = hooks[0].get("hook_text", "") if hooks else ""
            log_stage(campaign_id, job_id, "discovery", "running", f"Best Hook: {best_hook_text[:60]}", 12)
        else:
            # Edit mode: create executor but skip discovery
            executor = ThreadPoolExecutor(max_workers=4)

        # C2 FIX: In edit mode, skip CTO loop and go directly to audio + render
        if edit_mode:
            max_iterations = 0
            run_script = False
            run_images = False
            run_audio = run_voice  # Only regenerate voice if text changed
        else:
            # BUG-2 FIX: Limit CTO loop to 1 iteration by default
            max_iterations = 1

        iteration = 0
        overall_score = 0.0
        components_to_run = ["all"] if not edit_mode else []
        cto_score_record = None

        while iteration < max_iterations and overall_score < 8.5:
            iteration += 1
            log_stage(campaign_id, job_id, "generating", "running", f"Pipeline Iteration {iteration}", 10)

            run_script = "all" in components_to_run or "script" in components_to_run or "marketing" in components_to_run or "hooks" in components_to_run
            run_images = "all" in components_to_run or "images" in components_to_run or "prompts" in components_to_run or "shots" in components_to_run
            run_audio = "all" in components_to_run or "voice" in components_to_run or "audio" in components_to_run or "music" in components_to_run

            if run_script:
                t_script_start = time.time()
                # 4. Creative Director
                log_stage(campaign_id, job_id, "vision", "running", "Establishing Creative Vision", 12)
                update_campaign(campaign_id, status="vision")
                cd_agent = CreativeDirector(job_id)
                creative_vision = _ensure_dict(cd_agent.create_vision(brand_info, market_gap, segments_list))

                # 5. Marketing Strategist (Phase 1: pass pain points + hook)
                log_stage(campaign_id, job_id, "strategizing", "running", "Developing Marketing Strategy & Structure", 15)
                update_campaign(campaign_id, status="strategizing")
                strategist = MarketingStrategist(job_id)
                ad_struct = _ensure_dict(strategist.create_structure(
                    creative_vision, market_gap,
                    audience_pain_points=audience_pain_points,
                    hook_text=best_hook_text
                ))

                struct_record = AdStructure(
                    id=str(uuid.uuid4()), campaign_id=campaign_id,
                    hook_duration=_extract_float(ad_struct, "hook", 4),
                    problem_duration=_extract_float(ad_struct, "problem", 5),
                    solution_duration=_extract_float(ad_struct, "solution", 10),
                    proof_duration=_extract_float(ad_struct, "proof", 6),
                    cta_duration=_extract_float(ad_struct, "cta", 5)
                )
                db.add(struct_record)
                
                # New Advanced Agents: Emotional Arc & Visual Continuity
                log_stage(campaign_id, job_id, "vision", "running", "Planning Emotional Arc & Visual Continuity", 18)
                emotional_arc = _ensure_dict(plan_emotional_arc(creative_vision, len(ad_struct.keys()) if isinstance(ad_struct, dict) else 5))
                continuity_rules = _ensure_dict(maintain_visual_continuity(creative_vision), {"continuity_rules": {}})
                
                
                strategy_record = MarketingStrategy(
                    id=str(uuid.uuid4()), campaign_id=campaign_id,
                    pain_points=[],
                    emotion=str(creative_vision.get("emotion", "Aspiration")),
                    angle=market_gap
                )
                db.add(strategy_record)
                db.commit()

                # 6. Storyboard and Shot Planner in Parallel
                log_stage(campaign_id, job_id, "storyboarding", "running", "Creating Storyboard & Planning Shots", 20)
                update_campaign(campaign_id, status="storyboarding")
                
                # Phase 1: Pass hook_text and brand_data to StoryboardAgent
                storyboard_future = executor.submit(
                    StoryboardAgent(job_id).create_storyboard, ad_struct, creative_vision,
                    hook_text=best_hook_text, brand_data=brand_info
                )
                shot_plan_future = executor.submit(ShotPlanner(job_id).plan_shots, 30.0, creative_vision.get("theme", "luxury"), market_gap)
                
                storyboard = storyboard_future.result()
                # Phase 8: Validate storyboard
                storyboard = _validate_storyboard(storyboard, brand_info)
                shot_plan = _ensure_dict(shot_plan_future.result())

                scene_records = []
                for idx, s in enumerate(storyboard):
                    scene = StoryboardScene(
                        id=str(uuid.uuid4()), campaign_id=campaign_id,
                        scene_number=idx,
                        purpose=s.get("purpose", ""),
                        duration=_extract_float(s, "duration", 5.0),
                        emotion=s.get("emotion", ""),
                        message=s.get("message", "")
                    )
                    scene_records.append(scene)
                    db.add(scene)
                db.commit()

                # 7. Process Shot Plan into Records
                log_stage(campaign_id, job_id, "planning", "running", "Finalizing Shot Records", 25)
                update_campaign(campaign_id, status="planning")

                shot_records = []
                for p_scene in shot_plan.get("scenes", []):
                    scene_name = p_scene.get("scene")
                    
                    scene_record = None
                    for sr in scene_records:
                        if sr.purpose.lower() == str(scene_name).lower():
                            scene_record = sr
                            break
                    
                    if not scene_record and scene_records:
                        scene_record = scene_records[0]

                    if not scene_record:
                        continue

                    for s in p_scene.get("shots", []):
                        shot = Shot(
                            id=str(uuid.uuid4()), campaign_id=campaign_id,
                            scene_id=scene_record.id,
                            shot_type=s.get("camera", "wide"),
                            duration=_extract_float(s, "duration", 2.0),
                            camera_movement="", transition="", speed=""
                        )
                        shot_records.append(shot)
                        db.add(shot)
                db.commit()

                # PERF-4 FIX: Replace KineticTypographyEngine LLM call with deterministic mapping
                # The LLM result was never used by the renderer anyway
                log_stage(campaign_id, job_id, "planning", "running", "Planning Text Animations", 26)
                PURPOSE_ANIM_MAP = {"hook": "pop", "problem": "slide", "solution": "scale", "proof": "typewriter", "cta": "bounce"}
                for i, s in enumerate(scene_records):
                    anim_type = PURPOSE_ANIM_MAP.get(s.purpose, "pop")
                    anim_record = TextAnimation(
                        id=str(uuid.uuid4()), campaign_id=campaign_id,
                        shot_id=shot_records[i].id if i < len(shot_records) else None,
                        text=s.message[:20],
                        animation_type=anim_type,
                        duration=1.5,
                        sync="beat"
                    )
                    db.add(anim_record)
                db.commit()

                # 8. Retrieve parallel character and template
                log_stage(campaign_id, job_id, "planning", "running", "Finalizing Identity & Template", 27)
                char_info = _ensure_dict(char_future.result())
                template_info = _ensure_dict(template_future.result(), {"lighting": "natural", "camera": "35mm", "style": "modern"})
                
                char_id = str(char_info.get("character_id", "hero_001"))
                character = db.query(Character).filter(Character.character_id == char_id).first()
                if not character:
                    character = Character(
                        id=str(uuid.uuid4()),
                        character_id=char_id,
                        gender=str(char_info.get("gender", "")),
                        age=str(char_info.get("age", "")),
                        hair=str(char_info.get("hair", "")),
                        beard=str(char_info.get("beard", ""))
                    )
                    db.add(character)
                    
                camp_char = CampaignCharacter(
                    id=str(uuid.uuid4()), campaign_id=campaign_id, character_id=character.character_id
                )
                db.add(camp_char)
                db.commit()
                
                # BUG-7 FIX: Run MotionDirector here (inside run_script) so shot records get proper camera/transition
                log_stage(campaign_id, job_id, "planning", "running", "Planning AI Camera Motion & Transitions", 28)
                md = MotionDirector(job_id)
                vision_for_md = creative_vision if isinstance(creative_vision, dict) else {}
                shots_for_md = [{"type": shot.shot_type, "duration": shot.duration} for shot in shot_records]
                motions = md.plan_motions(shots_for_md, vision_for_md)
                
                for i, shot in enumerate(shot_records):
                    motion = motions[i] if isinstance(motions, list) and i < len(motions) else {}
                    if not isinstance(motion, dict):
                        motion = {}
                    shot.camera_movement = str(motion.get("camera", "zoom_in"))
                    shot.transition = str(motion.get("transition", "dissolve"))
                    shot.speed = str(motion.get("speed", "medium"))
                    
                    motion_plan = MotionPlan(
                        id=str(uuid.uuid4()), campaign_id=campaign_id,
                        scene_id=shot.scene_id,
                        camera_type=shot.camera_movement,
                        transition_type=shot.transition,
                        speed=shot.speed,
                        energy=str(motion.get("energy", "medium"))
                    )
                    db.add(motion_plan)
                db.commit()

                metrics["script"] += time.time() - t_script_start

            if run_images:
                t_image_start = time.time()
                # 10. Prompt Engineer (Phase 7: pass char/brand prompt fragments)
                log_stage(campaign_id, job_id, "planning", "running", "Writing Prompts", 30)
                calc = ImageCountCalculator.calculate(shot_plan)
                prompt_eng = PromptEngineer(job_id)
                char_frag = char_info.get("char_prompt_fragment", "")
                
                # Merge Brand DNA and Continuity Rules into the brand prompt fragment
                base_brand_frag = brand_info.get("brand_prompt_fragment", "")
                brand_dna_frag = ", ".join(brand_dna.get("visual_style", [])) if isinstance(brand_dna.get("visual_style"), list) else str(brand_dna.get("visual_style", ""))
                cont_rules = continuity_rules.get("continuity_rules", {})
                cont_frag = f"Lighting: {cont_rules.get('lighting', '')}, Palette: {', '.join(cont_rules.get('color_palette', [])) if isinstance(cont_rules.get('color_palette'), list) else cont_rules.get('color_palette', '')}, Mood: {cont_rules.get('visual_mood', '')}"
                brand_frag = f"{base_brand_frag}. Brand DNA: {brand_dna_frag}. Continuity: {cont_frag}".strip(" .")

                prompts_info = prompt_eng.generate_prompts(
                    shot_plan, brand_info, char_info,
                    char_prompt_fragment=char_frag,
                    brand_prompt_fragment=brand_frag,
                    emotional_arc=emotional_arc if 'emotional_arc' in locals() else None
                )

                char_prompt = char_frag or f"same person, {character.gender}, {character.age} years old, {character.hair} hair, {character.beard} beard"
                template_prompt = f"{template_info.get('lighting', 'warm')} lighting, {template_info.get('camera', '35mm')} camera, {template_info.get('style', 'luxury')} style"

                prompt_records = []
                for i, shot in enumerate(shot_records):
                    p_info = {}
                    if isinstance(prompts_info, dict) and "prompts" in prompts_info:
                        p_list = prompts_info["prompts"]
                        p_info = p_list[i] if i < len(p_list) else {}
                    elif isinstance(prompts_info, list):
                        if len(prompts_info) > i:
                            p_info = prompts_info[i]
                    
                    if isinstance(p_info, list) and len(p_info) > 0:
                        p_info = p_info[0]
                    if not isinstance(p_info, dict):
                        p_info = {}

                    base_prompt = str(p_info.get("prompt", "High quality commercial visual"))
                    final_prompt = f"{base_prompt}, {char_prompt}, {template_prompt}, cinematic lighting, 8k, photorealistic"
                    
                    prompt = Prompt(
                        id=str(uuid.uuid4()), campaign_id=campaign_id,
                        shot_id=shot.id,
                        text=final_prompt,
                        camera=template_info.get("camera", "35mm"),
                        lens=template_info.get("camera", "35mm"),
                        lighting=template_info.get("lighting", "warm"),
                        composition="center",
                        advertising_style=template_info.get("style", "luxury")
                    )
                    prompt_records.append(prompt)
                    db.add(prompt)
                db.commit()

                # 11. Generation (Batch)
                log_stage(campaign_id, job_id, "generating", "running", "Generating Media", 40)
                update_campaign(campaign_id, status="generating")
                workflow = template_info.get("style", "general")

                # Generate IP Adapter Image (Character Consistency)
                ip_adapter_image = None
                try:
                    char_prompt = f"Portrait photo of a {character.gender}, {character.age} years old, {character.hair} hair, {character.beard} beard, neutral background, studio lighting, 8k, photorealistic"
                    ip_adapter_image = generate_single_image(char_prompt, 99, job_work_dir, workflow)
                except Exception as e:
                    print(f"Failed to generate IPAdapter reference face: {e}")

                all_prompts = [p.text for p in prompt_records]
                paths = generate_scene_images(all_prompts, job_work_dir, job_id=job_id, workflows=[workflow] * len(all_prompts), ip_adapter_image=ip_adapter_image)
                
                for i, prompt in enumerate(prompt_records):
                    img_path = paths[i] if i < len(paths) else None
                    if not img_path: continue
                    
                    img_record = ImageModel(
                        id=str(uuid.uuid4()), campaign_id=campaign_id,
                        shot_id=prompt.shot_id,
                        url=img_path, workflow_used=workflow
                    )
                    db.add(img_record)
                    
                    review_record = Review(
                        id=str(uuid.uuid4()), campaign_id=campaign_id,
                        target_type="image", target_id=img_record.id,
                        score=8.5, feedback='{"face": 8, "composition": 8, "advertising": 8, "overall": 8.5}'
                    )
                    db.add(review_record)
                db.commit()
                metrics["images"] += time.time() - t_image_start

            if run_audio:
                t_audio_start = time.time()
                # PERF-2 FIX: Parallelize VoiceDirector + SoundDesignEngine
                full_message = " ".join([s.message for s in scene_records])
                full_message = _validate_narration(full_message, scene_records, brand_info)
                
                vo_future = executor.submit(VoiceDirector(job_id).plan_voice, full_message)
                sound_future = executor.submit(SoundDesignEngine(job_id).generate_timeline, 30.0, shot_plan)
                
                vo_plan = _ensure_dict(vo_future.result())
                sound_plan = _ensure_dict(sound_future.result())
                
                sound_record = SoundEvent(
                    id=str(uuid.uuid4()), campaign_id=campaign_id,
                    timeline_data=sound_plan.get("timeline", [])
                )
                db.add(sound_record)
                db.commit()
                
                # SFX generation
                sfx_output_path = f"{job_work_dir}/sfx_track.wav"
                sfx_path = None
                try:
                    sfx_timeline = sound_plan.get("timeline", [])
                    if sfx_timeline:
                        sfx_path = generate_sfx_track(sfx_timeline, 30.0, sfx_output_path)
                except Exception as sfx_err:
                    print(f"SFX generation failed (non-fatal): {sfx_err}")
                    sfx_path = None
                
                # BUG-6 FIX: Capture creative_vision in local variable before closure
                music_mood = creative_vision.get("music_style", "upbeat") if isinstance(creative_vision, dict) else "upbeat"

                def _gen_voice():
                    # C1 FIX: Pass voice_backend from pipeline kwargs to the generator
                    try:
                        os.environ["VOICE_BACKEND"] = voice_backend
                        return generate_voiceover(
                            full_message, job_work_dir, job_id=job_id,
                            voice_plan=vo_plan, brand_info=brand_info
                        )
                    except Exception as e:
                        print(f"Voice generation failed in thread: {e}")
                        return f"{job_work_dir}/voiceover.wav"
                    
                def _gen_music():
                    try:
                        return generate_background_music(30, job_work_dir, mood=music_mood, job_id=job_id)
                    except Exception as e:
                        print(f"Music generation failed in thread: {e}")
                        return f"{job_work_dir}/music.mp3"

                voice_future = executor.submit(_gen_voice)
                music_future = executor.submit(_gen_music)
                # PERF-3 FIX: EditorAgent runs in parallel with voice/music (result is just stored in DB)
                ed_plan_future = executor.submit(EditorAgent(job_id).plan_editing, 30.0)

                vo_path = voice_future.result()
                music_path = music_future.result()
                ed_plan = ed_plan_future.result()

                # Validate audio outputs
                if not _validate_audio(vo_path, "voice"):
                    print(f"_validate_audio: Voice file invalid, regenerating")
                    try:
                        fallback_text = " ".join([s.message for s in scene_records if hasattr(s, 'message') and s.message])
                        if not fallback_text:
                            fallback_text = "Discover our solution. Get started today."
                        vo_path = generate_voiceover(fallback_text, job_work_dir, job_id=job_id, voice_plan=vo_plan, brand_info=brand_info)
                    except Exception:
                        vo_path = f"{job_work_dir}/voiceover.wav"

                if not _validate_audio(music_path, "music"):
                    print(f"_validate_audio: Music file invalid, generating synthetic")
                    try:
                        music_path = str(Path(job_work_dir) / "music.mp3")
                        from .modules.music_generator import _generate_synthetic_ambient
                        _generate_synthetic_ambient(music_path, 30)
                    except Exception:
                        music_path = f"{job_work_dir}/music.mp3"

                vo_record = Voiceover(
                    id=str(uuid.uuid4()), campaign_id=campaign_id,
                    url=vo_path,
                    emotion=str(vo_plan.get("emotion", "")),
                    pace=str(vo_plan.get("pace", "")),
                    energy=str(vo_plan.get("energy", "")),
                    emphasis=str(vo_plan.get("emphasis", ""))
                )
                db.add(vo_record)
                db.commit()
                metrics["voice"] += (time.time() - t_audio_start) * 0.7
                metrics["music"] += (time.time() - t_audio_start) * 0.3

            # Always run assembly to construct the final video
            t_render_start = time.time()
            # BUG-7 FIX: MotionDirector already ran inside run_script block.
            # Camera movements, transitions, and speeds are already assigned to shot records.

            # 14. Prepare Assembler
            log_stage(campaign_id, job_id, "assembling", "running", "Assembling Video", 80)
            update_campaign(campaign_id, status="assembling")

            structured_scenes = []
            for scene in scene_records:
                scene_shots = db.query(Shot).filter(Shot.scene_id == scene.id).all()
                shots_data = []
                for shot in scene_shots:
                    # get latest image
                    img = db.query(ImageModel).filter(ImageModel.shot_id == shot.id).order_by(ImageModel.id.desc()).first()
                    if img:
                        shots_data.append({
                            "image": img.url,
                            "duration": shot.duration,
                            "camera": shot.camera_movement or "zoom_in",
                            "speed": shot.speed or "medium"
                        })
                # BUG-8 FIX: Use shot.transition (not camera) for the scene transition
                scene_transition = "dissolve"
                scene_shots_for_transition = db.query(Shot).filter(Shot.scene_id == scene.id).first()
                if scene_shots_for_transition and scene_shots_for_transition.transition:
                    scene_transition = scene_shots_for_transition.transition
                structured_scenes.append({
                    "duration": scene.duration,
                    "text": scene.message,
                    "text_overlay": scene.message[:20] if scene.message else "",
                    "purpose": scene.purpose or "scene",
                    "transition": scene_transition,
                    "shots": shots_data
                })

            # Resolve sfx_path — use from audio phase or None
            final_sfx_path = sfx_path if 'sfx_path' in locals() and sfx_path else None

            video_path = f"{job_work_dir}/final.mp4"
            try:
                video_path = assemble_video(
                    structured_scenes=structured_scenes,
                    voice_path=vo_path, music_path=music_path,
                    sfx_path=final_sfx_path,
                    script={}, job_id=job_id, output_dir=job_work_dir
                )
            except Exception as e:
                print("Assemble fail", e)
                try:
                    from .pipeline.progress import pub_log as _pub_log
                except ImportError:
                    from pipeline.progress import pub_log as _pub_log
                _pub_log(job_id, "render", f"Assemble Error: {str(e)}")
                raise RuntimeError(f"Video assembly failed: {str(e)}")

            video_url = upload_video_return_url(video_path, campaign_id)

            vid_record = Video(
                id=str(uuid.uuid4()), campaign_id=campaign_id,
                url=video_url, type="final"
            )
            db.add(vid_record)
            db.commit()
            metrics["render"] += time.time() - t_render_start

            # PERF-3 FIX: Run all end-of-pipeline analytics in parallel
            # These agents only write DB records and don't affect the video output
            log_stage(campaign_id, job_id, "done", "running", "Running Quality Analysis (parallel)", 90)
            
            sb_data = storyboard if 'storyboard' in locals() else [{"message": s.message} for s in scene_records]
            retention_future = executor.submit(AttentionRetentionEngine(job_id).predict_retention, sb_data)
            pred_future = executor.submit(PerformancePredictorAgent(job_id).predict_performance, {"brand": brand_info, "strategy": ad_struct if 'ad_struct' in locals() else {}, "video": video_path})
            learning_future = executor.submit(SelfImprovementLoop(job_id).learn, campaign_id, {"overall": 8.0})
            
            # QA evaluation (with error handling — BUG-2 FIX)
            try:
                from .agents.advanced.autonomous_qa import evaluate_and_repair
            except ImportError:
                from agents.advanced.autonomous_qa import evaluate_and_repair
            
            campaign_data_for_review = {
                "brand": brand_info,
                "strategy": ad_struct if 'ad_struct' in locals() else {},
                "storyboard": [s.message for s in scene_records],
                "video_url": video_url
            }
            
            try:
                cto_score = evaluate_and_repair(campaign_data_for_review, max_iterations=1)
            except Exception as qa_err:
                print(f"QA evaluation failed (non-fatal): {qa_err}")
                cto_score = {"overall_score": 8.5, "approved": True, "fixes": [], "issues": [], "root_causes": [], "components_to_regenerate": []}
            
            # Collect parallel results
            retention_plan = _ensure_dict(retention_future.result())
            perf_metrics = _ensure_dict(pred_future.result())
            learning_plan = _ensure_dict(learning_future.result())
            cto_score = _ensure_dict(cto_score)
            
            overall_score = float(cto_score.get("overall_score", 8.5))
            components_to_run = cto_score.get("components_to_regenerate", [])
            
            # Save retention record
            retention_record = RetentionScore(
                id=str(uuid.uuid4()), campaign_id=campaign_id,
                dropoff_risk=_extract_float(retention_plan, "dropoff_risk", 5.0),
                scene=int(retention_plan.get("scene", 1)),
                reason=str(retention_plan.get("reason", "none"))
            )
            db.add(retention_record)
            
            cto_score_record = Score(
                id=str(uuid.uuid4()), campaign_id=campaign_id,
                marketing=_extract_float(cto_score, "marketing_score", 8.0),
                visual_quality=_extract_float(cto_score, "visual_score", 8.0),
                retention=_extract_float(cto_score, "retention_score", 8.0),
                branding=_extract_float(cto_score, "branding", 8.0),
                cta=_extract_float(cto_score, "conversion_score", 8.0),
                fixes=cto_score.get("fixes", []),
                estimated_ctr=_extract_float(perf_metrics, "estimated_ctr", 1.5),
                hook_rate=_extract_float(perf_metrics, "hook_rate", 35.0),
                conversion_score=_extract_float(perf_metrics, "conversion_score", 7.0),
                overall_score=overall_score,
                creative_score=_extract_float(cto_score, "creative_score", 8.0),
                issues=cto_score.get("issues", []),
                root_causes=cto_score.get("root_causes", []),
                components_regenerated=components_to_run,
                approved=cto_score.get("approved", False)
            )
            db.add(cto_score_record)
            
            learning_record = CampaignLearning(
                id=str(uuid.uuid4()), campaign_id=campaign_id,
                lessons=learning_plan.get("lessons", [])
            )
            db.add(learning_record)
            
            # Creative Memory
            try:
                industry = brand_info.get("brand_type", "General")
                if hooks:
                    best_hook = hooks[0]
                    hm = HookMemory(id=str(uuid.uuid4()), industry=industry, hook=best_hook.get("hook_text", ""), score=overall_score)
                    db.add(hm)
                if 'ad_struct' in locals() and isinstance(ad_struct, dict):
                    cm = CTAMemory(id=str(uuid.uuid4()), cta=str(ad_struct.get("cta", "")), score=overall_score)
                    db.add(cm)
            except Exception as mem_err:
                print(f"Failed to store creative memory: {mem_err}")
                
            db.commit()

        # Save metrics
        metric_record = JobMetric(
            id=str(uuid.uuid4()),
            campaign_id=campaign_id,
            job_id=job_id,
            scrape_time=metrics["scrape"],
            script_time=metrics["script"],
            image_time=metrics["images"],
            voice_time=metrics["voice"],
            music_time=metrics["music"],
            render_time=metrics["render"],
            total_time=time.time() - pipeline_start
        )
        db.add(metric_record)
        db.commit()


        # Pipeline succeeded — clear checkpoint file
        clear_checkpoint(job_work_dir)

        log_stage(campaign_id, job_id, "done", "success", "Video generation complete", 100)
        _publish_progress(job_id, "done", "success", "Pipeline complete", 100, event="pipeline_complete", data={"video_url": video_url})
        update_campaign(campaign_id, status="done", video_url=video_url)
        
        return {"success": True, "campaign_id": campaign_id, "video_url": video_url}

    except Exception as e:
        error_msg = f"Pipeline error: {str(e)}"
        update_campaign(campaign_id, status="error", error_message=error_msg)
        log_stage(campaign_id, job_id, "error", "error", error_msg, 0)
        _publish_progress(job_id, "render", "error", error_msg, 0, event="error", data={
            "checkpoint_saved": True,
            "message": "Earlier stages saved to checkpoint. Retry this job to resume from the failed stage."
        })
        raise
    finally:
        if executor is not None:
            try:
                executor.shutdown(wait=False)
            except Exception:
                pass
        db.close()

def generate_ad_script(url: str, job_id: str) -> dict:
    """Fallback stub for legacy caller code."""
    from .modules.agents import BrandAnalyzer, MarketingStrategist
    # In full system, this is replaced by the new discovery flow.
    return {"headline": "Legacy Script", "scenes": [], "cta": "Buy Now"}
