from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import types

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


if "pydub" not in sys.modules:
    pydub_stub = types.ModuleType("pydub")
    generators_stub = types.ModuleType("pydub.generators")

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

    class _SineStub:
        def __init__(self, _freq):
            pass

        def to_audio_segment(self, duration=1000):
            _ = duration
            return _AudioSegmentStub()

    pydub_stub.AudioSegment = _AudioSegmentStub
    generators_stub.Sine = _SineStub
    sys.modules["pydub"] = pydub_stub
    sys.modules["pydub.generators"] = generators_stub

import jobs
from models import Base, Campaign, JobLog, Video


class FakeRedis:
    def __init__(self):
        self.store = {}

    def hset(self, key, mapping):
        bucket = self.store.setdefault(key, {})
        bucket.update(mapping)

    def hgetall(self, key):
        return dict(self.store.get(key, {}))


def test_pipeline_smoke_transitions_db_and_redis(tmp_path, monkeypatch):
    db_path = tmp_path / "smoke.db"
    engine = create_engine(f"sqlite:///{db_path}")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(jobs, "engine", engine)
    monkeypatch.setattr(jobs, "SessionLocal", SessionLocal)
    monkeypatch.setattr(jobs, "redis_conn", FakeRedis())
    monkeypatch.setattr(jobs, "get_current_job", lambda: SimpleNamespace(id="job-smoke-1"))

    campaign_id = "camp-smoke-1"
    session = SessionLocal()
    session.add(
        Campaign(
            id=campaign_id,
            user_id="demo-user",
            business_url="https://example.com",
            status="queued",
        )
    )
    session.commit()
    session.close()

    from modules.agents import LLMAgent
    def fake_generate(*args, **kwargs):
        raise Exception("Mock LLM to trigger fallbacks")
    monkeypatch.setattr(LLMAgent, "generate", fake_generate)

    def fake_scrape(url):
        return {
            "url": url,
            "company_name": "Example Co",
            "description": "Example description",
            "products": ["A", "B"],
            "industry": "technology",
            "call_to_action": "Get started",
        }

    def fake_script(_brand, **kwargs):
        return {
            "scenes": [
                {"description": f"scene {i}", "text": f"t{i}", "duration": 6}
                for i in range(5)
            ],
            "narration": "hello world narration",
            "music_suggestion": "upbeat",
        }

    def fake_images(descriptions, output_dir, **kwargs):
        paths = []
        for i, _ in enumerate(descriptions):
            p = Path(output_dir) / f"scene_{i:02d}.png"
            p.write_bytes(b"png")
            paths.append(str(p))
        return paths

    def fake_voice(_text, output_dir, **kwargs):
        p = Path(output_dir) / "voice.wav"
        p.write_bytes(b"wav")
        return str(p)

    def fake_music(_duration, output_dir, _mood, **kwargs):
        p = Path(output_dir) / "music.mp3"
        p.write_bytes(b"mp3")
        return str(p)

    def fake_mix(_voice, _music, output_path, _gain=-18):
        p = Path(output_path)
        p.write_bytes(b"wavmix")
        return str(p)

    def fake_video(structured_scenes=None, voice_path=None, music_path=None, script=None, **kwargs):
        _ = structured_scenes
        _ = voice_path
        output_dir = kwargs.get("output_dir", ".")
        p = Path(output_dir) / "final_ad.mp4"
        p.write_bytes(b"mp4")
        return str(p)

    monkeypatch.setattr(jobs, "scrape_business_url", fake_scrape)
    monkeypatch.setattr(jobs, "generate_ad_script", fake_script)
    monkeypatch.setattr(jobs, "generate_scene_images", fake_images)
    monkeypatch.setattr(jobs, "generate_voiceover", fake_voice)
    monkeypatch.setattr(jobs, "generate_background_music", fake_music)
    monkeypatch.setattr(jobs, "mix_voice_with_music", fake_mix)
    monkeypatch.setattr(jobs, "assemble_video", fake_video)
    monkeypatch.setattr(jobs, "upload_video_return_url", lambda *_: "http://minio.local/final.mp4")

    result = jobs.generate_ad(
        campaign_id=campaign_id,
        url="https://example.com",
        user_id="demo-user",
    )

    assert result["success"] is True
    assert result["video_url"] == "http://minio.local/final.mp4"

    session = SessionLocal()
    campaign = session.query(Campaign).filter(Campaign.id == campaign_id).first()
    logs = session.query(JobLog).filter(JobLog.campaign_id == campaign_id).all()
    video = session.query(Video).filter(Video.campaign_id == campaign_id).first()
    session.close()

    assert campaign is not None
    assert campaign.status == "done"
    assert video is not None
    assert video.url == "http://minio.local/final.mp4"

    stages = [log.stage for log in logs if log.status == "success" or log.status == "running"]
    for expected in ["analyzing", "discovery", "vision", "assembling", "done"]:
        assert expected in stages

    redis_progress = jobs.redis_conn.hgetall("job:job-smoke-1")
    assert redis_progress.get("status") in ("success", "complete", "finished")
    assert redis_progress.get("stage") == "done"
