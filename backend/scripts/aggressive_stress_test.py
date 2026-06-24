#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import random
import statistics
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from PIL import Image, ImageDraw
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if "minio" not in sys.modules:
    minio_stub = type(sys)("minio")

    class _Minio:
        def __init__(self, *args, **kwargs):
            _ = args
            _ = kwargs

        def bucket_exists(self, *_args, **_kwargs):
            return True

        def make_bucket(self, *_args, **_kwargs):
            return None

        def fput_object(self, *_args, **_kwargs):
            return None

        def presigned_get_object(self, *_args, **_kwargs):
            return "http://localhost/fake.mp4"

    minio_stub.Minio = _Minio
    sys.modules["minio"] = minio_stub

if "pydub" not in sys.modules:
    pydub_stub = type(sys)("pydub")

    class _AudioSegmentStub:
        @staticmethod
        def from_file(_path):
            return _AudioSegmentStub()

        @staticmethod
        def silent(duration=0):
            _ = duration
            return _AudioSegmentStub()

        def export(self, _path, format="mp3"):
            _ = format
            Path(_path).write_bytes(b"audio")
            return None

        def __add__(self, _value):
            return self

        def __mul__(self, _value):
            return self

        def __getitem__(self, _slice):
            return self

        def overlay(self, _other):
            return self

        def __len__(self):
            return 1000

    pydub_stub.AudioSegment = _AudioSegmentStub
    sys.modules["pydub"] = pydub_stub

import jobs
from models import Base, Campaign, JobLog
from modules.scraper import scrape_business_url


THREAD_STATE = threading.local()


@dataclass
class JobPlan:
    job_id: str
    url: str
    failure_mode: str | None
    force_stage: str | None = None


@dataclass
class JobResult:
    job_id: str
    url: str
    failure_mode: str | None
    ok: bool
    error: str | None
    duration_s: float
    stage_count: int
    success_stages: list[str]
    failed_stages: list[str]
    retries: int
    video_url: str | None


class StressRedis:
    def __init__(self, failure_jobs: set[str] | None = None):
        self._store: dict[str, dict[str, str]] = {}
        self._kv: dict[str, str] = {}
        self._lock = threading.Lock()
        self._failure_jobs = failure_jobs or set()
        self._hset_calls: dict[str, int] = {}

    def hset(self, key, mapping):
        job_id = key.split(":", 1)[-1]
        with self._lock:
            self._hset_calls[job_id] = self._hset_calls.get(job_id, 0) + 1
            if job_id in self._failure_jobs and self._hset_calls[job_id] == 3:
                raise ConnectionError("simulated redis disconnect")
            bucket = self._store.setdefault(key, {})
            bucket.update(mapping)

    def hgetall(self, key):
        with self._lock:
            return dict(self._store.get(key, {}))

    def get(self, key):
        with self._lock:
            return self._kv.get(key)

    def setex(self, key, ttl, value):
        _ = ttl
        with self._lock:
            self._kv[key] = value

    def ping(self):
        return True


class PropagatingExecutor:
    def __init__(self, max_workers: int | None = None):
        from concurrent.futures import ThreadPoolExecutor as RealExecutor

        self._executor = RealExecutor(max_workers=max_workers)

    def __enter__(self):
        self._executor.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._executor.__exit__(exc_type, exc, tb)

    def submit(self, fn, *args, **kwargs):
        plan = getattr(THREAD_STATE, "plan", None)

        def wrapped(*inner_args, **inner_kwargs):
            THREAD_STATE.plan = plan
            return fn(*inner_args, **inner_kwargs)

        return self._executor.submit(wrapped, *args, **kwargs)


class NullJob:
    def __init__(self, job_id: str):
        self.id = job_id



def _make_campaign(session_maker, job_id: str, url: str) -> str:
    db = session_maker()
    try:
        campaign_id = uuid.uuid4().hex
        db.add(
            Campaign(
                id=campaign_id,
                user_id="stress-user",
                job_id=job_id,
                business_url=url,
                status="queued",
            )
        )
        db.commit()
        return campaign_id
    finally:
        db.close()



def _live_or_fallback_brand(url: str) -> dict[str, Any]:
    try:
        return scrape_business_url(url)
    except Exception:
        return {
            "url": url,
            "fetch_method": "fallback",
            "company_name": "Google",
            "tagline": "Search and AI services",
            "description": "Search and AI services",
            "products": ["Search", "Cloud", "Workspace"],
            "industry": "technology",
            "call_to_action": "Learn more",
            "images": [],
            "colors": [],
            "tone": "professional",
            "target_audience": "general",
        }



def _brand_for_job(plan: JobPlan, brand_data: dict[str, Any]) -> dict[str, Any]:
    _ = plan
    return brand_data



def _script_for_job(plan: JobPlan, brand_data: dict[str, Any]) -> dict[str, Any]:
    if plan.failure_mode == "ollama_timeout":
        raise TimeoutError("simulated ollama timeout")

    company = brand_data.get("company_name", "Brand")
    scenes = []
    for idx in range(5):
        scenes.append(
            {
                "id": idx,
                "description": f"{company} scene {idx + 1} with bold product visuals and clean composition",
                "text": f"{company} value {idx + 1}",
                "duration": 6,
                "narration": f"Scene {idx + 1} narration for {company}.",
            }
        )

    return {
        "headline": f"{company} in Focus",
        "cta": brand_data.get("call_to_action", "Learn more"),
        "scenes": scenes,
        "narration": f"{company} helps people do more with less friction.",
        "music_suggestion": "upbeat and modern",
    }



def _image_for_job(plan: JobPlan, descriptions: list[str], output_dir: str) -> list[str]:
    from modules import image_generator as image_mod

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    for idx, description in enumerate(descriptions):
        if plan.failure_mode == "comfyui_crash" and idx == 2:
            # Simulate one bad scene; the app should keep the other scenes.
            raise RuntimeError("simulated ComfyUI crash")
        if plan.failure_mode == "gpu_oom" and idx == 1:
            raise RuntimeError("CUDA out of memory")

        image = Image.new("RGB", (1024, 576), color=((20 + idx * 30) % 255, (60 + idx * 45) % 255, (120 + idx * 20) % 255))
        draw = ImageDraw.Draw(image)
        draw.text((32, 32), f"{plan.job_id[:8]} scene {idx + 1}", fill=(255, 255, 255))
        draw.text((32, 80), description[:72], fill=(230, 230, 230))
        out_path = output_dir_path / f"scene_{idx:02d}.png"
        image.save(out_path)
        paths.append(str(out_path))

    return paths



def _voice_for_job(plan: JobPlan, text: str, output_dir: str) -> str:
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    out_path = output_dir_path / "voiceover.wav"

    if plan.failure_mode == "tts_failure":
        # Simulate the turbo backend failing. The app's fallback chain should still produce output.
        out_path.write_bytes(b"silence")
        return str(out_path)

    if plan.failure_mode == "missing_audio_file":
        raise FileNotFoundError("simulated missing audio file")

    out_path.write_bytes(text.encode("utf-8")[:32] or b"voice")
    return str(out_path)



def _music_for_job(plan: JobPlan, duration_seconds: int, output_dir: str, mood: str = "upbeat") -> str:
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    out_path = output_dir_path / "music.mp3"

    if plan.failure_mode == "slow_network":
        time.sleep(0.6)

    if plan.failure_mode == "missing_audio_file":
        raise FileNotFoundError("simulated missing music file")

    out_path.write_bytes(f"music:{duration_seconds}:{mood}".encode("utf-8"))
    return str(out_path)



def _mix_for_job(plan: JobPlan, voice_path: str, music_path: str, output_path: str, music_gain_db: int = -18) -> str:
    _ = music_gain_db
    if plan.failure_mode == "ffmpeg_failure":
        raise RuntimeError("simulated ffmpeg encode failure")

    out = Path(output_path)
    out.write_bytes((Path(voice_path).read_bytes() if Path(voice_path).exists() else b"") + (Path(music_path).read_bytes() if Path(music_path).exists() else b""))
    return str(out)



def _video_for_job(plan: JobPlan, scenes: list[dict[str, Any]], audio_path: str, output_dir: str) -> str:
    _ = scenes
    _ = audio_path
    if plan.failure_mode == "ffmpeg_failure":
        raise RuntimeError("simulated ffmpeg final render failure")

    out = Path(output_dir) / "final_ad.mp4"
    out.write_bytes(f"video:{plan.job_id}".encode("utf-8"))
    return str(out)



def _job_runner(plan: JobPlan, campaign_id: str) -> JobResult:
    start = time.perf_counter()
    THREAD_STATE.job_id = plan.job_id
    THREAD_STATE.failure_mode = plan.failure_mode
    THREAD_STATE.retries = 0
    THREAD_STATE.retry_counts = {}

    try:
        result = jobs.generate_ad(
            campaign_id=campaign_id,
            url=plan.url,
            user_id="stress-user",
            job_id=plan.job_id,
        )
        ok = True
        error = None
        video_url = result.get("video_url")
        total_retries = result.get("total_retries", 0)
    except Exception as exc:
        ok = False
        error = str(exc)
        video_url = None
        total_retries = 0

    duration_s = time.perf_counter() - start

    db = jobs.SessionLocal()
    try:
        logs = db.query(JobLog).filter(JobLog.campaign_id == campaign_id).all()
    finally:
        db.close()

    success_stages = [log.stage for log in logs if log.status == "success"]
    failed_stages = [log.stage for log in logs if log.status == "error"]

    return JobResult(
        job_id=plan.job_id,
        url=plan.url,
        failure_mode=plan.failure_mode,
        ok=ok,
        error=error,
        duration_s=duration_s,
        stage_count=len(logs),
        success_stages=success_stages,
        failed_stages=failed_stages,
        retries=total_retries,
        video_url=video_url,
    )



def main() -> int:
    base_url = "https://google.com"
    tmpdir = Path(tempfile.mkdtemp(prefix="creoad-stress-"))
    db_path = tmpdir / "stress.db"

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    session_maker = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    jobs.engine = engine
    jobs.SessionLocal = session_maker
    jobs.get_current_job = lambda: None

    brand_data = _live_or_fallback_brand(base_url)
    original_generate_scene_images = jobs.generate_scene_images
    original_generate_voiceover = jobs.generate_voiceover
    original_generate_background_music = jobs.generate_background_music
    original_mix_voice_with_music = jobs.mix_voice_with_music
    original_assemble_video = jobs.assemble_video
    original_thread_pool = jobs.ThreadPoolExecutor
    original_scrape = jobs.scrape_business_url
    original_script = jobs.generate_ad_script

    plans = [
        JobPlan(f"stress-{idx:02d}", f"{base_url}?case={idx}", failure_mode)
        for idx, failure_mode in enumerate(
            [
                None,
                "comfyui_crash",
                "tts_failure",
                "ffmpeg_failure",
                "ollama_timeout",
                "redis_disconnect",
                "gpu_oom",
                "slow_network",
                "missing_audio_file",
                None,
            ],
            start=1,
        )
    ]

    failure_jobs = {plan.job_id for plan in plans if plan.failure_mode == "redis_disconnect"}
    jobs.redis_conn = StressRedis(failure_jobs=failure_jobs)

    def scrape_wrapper(url: str):
        _ = url
        plan = getattr(THREAD_STATE, "plan", None)
        if plan and plan.failure_mode == "slow_network":
            time.sleep(0.5)
        return brand_data

    def script_wrapper(brand: dict[str, Any]):
        plan = getattr(THREAD_STATE, "plan", None)
        return _script_for_job(plan, brand)

    def images_wrapper(descriptions: list[str], output_dir: str):
        plan = getattr(THREAD_STATE, "plan", None)
        return _image_for_job(plan, descriptions, output_dir)

    def voice_wrapper(text: str, output_dir: str, voice: str = "female"):
        _ = voice
        plan = getattr(THREAD_STATE, "plan", None)
        return _voice_for_job(plan, text, output_dir)

    def music_wrapper(duration_seconds: int, output_dir: str, mood: str = "upbeat"):
        plan = getattr(THREAD_STATE, "plan", None)
        return _music_for_job(plan, duration_seconds, output_dir, mood)

    def mix_wrapper(voice_path: str, music_path: str, output_path: str, music_gain_db: int = -18):
        plan = getattr(THREAD_STATE, "plan", None)
        return _mix_for_job(plan, voice_path, music_path, output_path, music_gain_db)

    def video_wrapper(scenes: list[dict[str, Any]], audio_path: str, output_dir: str):
        plan = getattr(THREAD_STATE, "plan", None)
        return _video_for_job(plan, scenes, audio_path, output_dir)

    jobs.scrape_business_url = scrape_wrapper
    jobs.generate_ad_script = script_wrapper
    jobs.generate_scene_images = images_wrapper
    jobs.generate_voiceover = voice_wrapper
    jobs.generate_background_music = music_wrapper
    jobs.mix_voice_with_music = mix_wrapper
    jobs.assemble_video = video_wrapper
    jobs.ThreadPoolExecutor = PropagatingExecutor

    campaign_ids = {
        plan.job_id: _make_campaign(session_maker, plan.job_id, plan.url)
        for plan in plans
    }

    def run_plan(plan: JobPlan) -> JobResult:
        THREAD_STATE.plan = plan
        return _job_runner(plan, campaign_ids[plan.job_id])

    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_plan, plan) for plan in plans]
        results = [future.result() for future in as_completed(futures)]
    wall_time = time.perf_counter() - wall_start

    process_user_s = 0.0
    process_sys_s = 0.0
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        process_user_s = float(usage.ru_utime)
        process_sys_s = float(usage.ru_stime)
        peak_rss_kb = int(getattr(usage, "ru_maxrss", 0))
    except Exception:
        peak_rss_kb = 0

    # Calculate recovery statistics
    total_attempts = sum(r.retries for r in results)
    avg_retries = round(total_attempts / len(results), 2) if results else 0
    recovered_jobs = sum(1 for r in results if r.ok and r.retries > 0)
    
    # Identify stages that benefited from retry
    stages_with_retries = {}
    for log in logs if 'logs' in locals() else []:
        if log.status == "retrying":
            stage = log.stage
            stages_with_retries[stage] = stages_with_retries.get(stage, 0) + 1

    summary = {
        "input_url": base_url,
        "total_jobs": len(results),
        "successful_jobs": sum(1 for r in results if r.ok),
        "failed_jobs": sum(1 for r in results if not r.ok),
        "recovered_jobs": recovered_jobs,
        "wall_time_s": round(wall_time, 3),
        "mean_job_time_s": round(statistics.mean(r.duration_s for r in results), 3),
        "max_job_time_s": round(max(r.duration_s for r in results), 3),
        "cpu_user_s": round(process_user_s, 3),
        "cpu_sys_s": round(process_sys_s, 3),
        "peak_rss_kb": peak_rss_kb,
        "gpu_utilization": "unavailable in this environment",
        "vram_usage": "unavailable in this environment",
        "total_retry_attempts": total_attempts,
        "average_retries_per_job": avg_retries,
        "recovery_effectiveness": f"{(recovered_jobs / len(results) * 100):.1f}%" if results else "N/A",
        "retry_counts": {r.job_id: r.retries for r in results},
        "failed_stages": {r.job_id: r.failed_stages for r in results if r.failed_stages},
        "final_export_status": {r.job_id: ("success" if r.ok else "failed") for r in results},
        "results": [asdict(r) for r in sorted(results, key=lambda item: item.job_id)],
    }

    report_path = tmpdir / "stress-report.json"
    report_path.write_text(json.dumps(summary, indent=2))

    print(json.dumps(summary, indent=2))
    print(f"REPORT_PATH={report_path}")

    jobs.scrape_business_url = original_scrape
    jobs.generate_ad_script = original_script
    jobs.generate_scene_images = original_generate_scene_images
    jobs.generate_voiceover = original_generate_voiceover
    jobs.generate_background_music = original_generate_background_music
    jobs.mix_voice_with_music = original_mix_voice_with_music
    jobs.assemble_video = original_assemble_video
    jobs.ThreadPoolExecutor = original_thread_pool

    return 0 if summary["failed_jobs"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
