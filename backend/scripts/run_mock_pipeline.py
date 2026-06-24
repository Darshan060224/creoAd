#!/usr/bin/env python3
from pathlib import Path
import os
import sys
import uuid
import subprocess
import argparse

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite:///./backend/samples/mock_flow.db")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Campaign
import types

# Provide a lightweight `minio` stub so `modules/storage.py` can be imported
if "minio" not in sys.modules:
    minio_stub = types.ModuleType("minio")
    class _Minio:
        def __init__(self, *args, **kwargs):
            pass
    minio_stub.Minio = _Minio
    sys.modules["minio"] = minio_stub

import jobs


def ensure_dirs():
    Path("backend/samples").mkdir(parents=True, exist_ok=True)
    Path("/tmp/creoAd_jobs").mkdir(parents=True, exist_ok=True)


def setup_db(db_path: str):
    engine = create_engine(db_path)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    # patch jobs to use this engine/session
    jobs.engine = engine
    jobs.SessionLocal = SessionLocal
    return engine, SessionLocal


def create_campaign(session_maker, url: str, user_id: str):
    db = session_maker()
    try:
        campaign_id = uuid.uuid4().hex
        c = Campaign(
            id=campaign_id,
            business_url=url,
            user_id=user_id,
            status="queued",
        )
        db.add(c)
        db.commit()
        return campaign_id
    finally:
        db.close()


def install_fakes(target_resolution=(1920, 1080)):
    # lightweight fakes that write real media to simulate pipeline
    from PIL import Image
    import wave
    import struct

    def fake_scrape(url):
        return {"url": url, "company_name": "Acme Co", "description": "Acme description", "call_to_action": "Buy"}

    def fake_script(_brand):
        return {
            "scenes": [{"description": f"scene {i}", "text": f"Acme value {i}", "duration": 6} for i in range(5)],
            "narration": "Acme helps businesses grow.",
            "music_suggestion": "Try Free Today",
        }

    def fake_images(descriptions, output_dir, aspect="landscape", overlay_texts=None):
        paths = []
        size = target_resolution
        for i, _ in enumerate(descriptions):
            p = Path(output_dir) / f"scene_{i:02d}.png"
            img = Image.new("RGB", size, color=(30 + i * 20, 60 + i * 15, 120 + i * 8))
            img.save(p, format="PNG")
            paths.append(str(p))
        return paths

    def comfy_generate_images(descriptions, output_dir, aspect="landscape", overlay_texts=None):
        # Best-effort: attempt to contact ComfyUI at localhost:8188 and POST a simple request.
        # ComfyUI APIs vary between setups; this function will try a common path and fall back to fake images.
        import socket
        try:
            sock = socket.create_connection(("127.0.0.1", 8188), timeout=1)
            sock.close()
        except Exception:
            return fake_images(descriptions, output_dir, aspect, overlay_texts)

        try:
            import requests
            results = []
            for i, desc in enumerate(descriptions):
                payload = {
                    "prompt": desc or "product shot, minimal background, cinematic lighting",
                    "width": target_resolution[0],
                    "height": target_resolution[1],
                }
                # This endpoint may not exist on all ComfyUI setups; try a few common paths
                urls = [
                    "http://127.0.0.1:8188/api/generate",
                    "http://127.0.0.1:8188/api/v1/generate",
                    "http://127.0.0.1:8188/generate",
                ]
                img_bytes = None
                for u in urls:
                    try:
                        r = requests.post(u, json=payload, timeout=10)
                        if r.status_code == 200 and r.content:
                            img_bytes = r.content
                            break
                    except Exception:
                        continue

                if not img_bytes:
                    return fake_images(descriptions, output_dir, aspect, overlay_texts)

                p = Path(output_dir) / f"scene_{i:02d}.png"
                p.write_bytes(img_bytes)
                results.append(str(p))
            return results
        except Exception:
            return fake_images(descriptions, output_dir, aspect, overlay_texts)

    def _write_silent_wav(path, duration_s=30, rate=44100):
        n_channels = 1
        sampwidth = 2
        n_frames = int(duration_s * rate)
        with wave.open(str(path), "w") as wf:
            wf.setnchannels(n_channels)
            wf.setsampwidth(sampwidth)
            wf.setframerate(rate)
            silence = struct.pack('<h', 0) * n_frames
            wf.writeframes(silence)

    def fake_voice(_text, output_dir):
        p = Path(output_dir) / "voice.wav"
        _write_silent_wav(p, duration_s=30)
        return str(p)

    def fake_music(_duration, output_dir, _mood):
        p = Path(output_dir) / "music.wav"
        _write_silent_wav(p, duration_s=_duration)
        return str(p)

    def fake_mix(voice, music, output_path, _gain=-18):
        # mix using ffmpeg amix
        out = Path(output_path)
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(voice),
            "-i",
            str(music),
            "-filter_complex",
            "[0:a][1:a]amix=inputs=2:duration=longest",
            "-c:a",
            "pcm_s16le",
            str(out),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return str(out)

    def fake_video(scenes, audio_path, output_dir):
        # scenes: list of dicts with image paths and durations
        out = Path(output_dir) / "final_ad.mp4"
        durations = [int(s.get("duration", 6)) for s in scenes]
        per_frame = durations[0] if durations else 6
        img_pattern = str(Path(output_dir) / "scene_%02d.png")
        cmd = [
            "ffmpeg",
            "-y",
            "-framerate",
            f"1/{per_frame}",
            "-i",
            img_pattern,
            "-i",
            str(audio_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            str(out),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return str(out)

    jobs.scrape_business_url = fake_scrape
    jobs.generate_ad_script = fake_script
    jobs.generate_scene_images = fake_images
    jobs.generate_voiceover = fake_voice
    jobs.generate_background_music = fake_music
    jobs.mix_voice_with_music = fake_mix
    jobs.assemble_video = fake_video
    jobs.upload_video_return_url = lambda path, cid: f"file://{path}"


def install_redis_and_job_stubs():
    class FakeRedis:
        def __init__(self):
            self.store = {}

        def hset(self, key, mapping):
            bucket = self.store.setdefault(key, {})
            bucket.update(mapping)

        def hgetall(self, key):
            return dict(self.store.get(key, {}))

        def ping(self):
            return True

    jobs.redis_conn = FakeRedis()
    jobs.get_current_job = lambda: None


def run():
    # parse CLI args for resolution and styling
    parser = argparse.ArgumentParser(description="Run mocked pipeline and produce sample ad")
    parser.add_argument("--resolution", default="1920x1080", help="Output resolution WxH, e.g. 2560x1440 or 1280x720")
    parser.add_argument("--headline-size", type=int, default=72, help="Headline font size")
    parser.add_argument("--value-size", type=int, default=48, help="Value text font size")
    parser.add_argument("--cta-size", type=int, default=56, help="CTA font size")
    parser.add_argument("--cta-text", default=None, help="CTA override text")
    parser.add_argument("--use-comfyui", action="store_true", help="Attempt to detect and use ComfyUI for image generation")

    # accept color args
    parser.add_argument("--headline-color", default="#FFFFFF", help="Headline color as hex, e.g. #FFFFFF")
    parser.add_argument("--value-color", default="#E6E6E6", help="Value text color as hex")
    parser.add_argument("--cta-box-color", dest="cta_box_color", default="#FF5A00", help="CTA box color hex")
    parser.add_argument("--cta-text-color", dest="cta_text_color", default="#FFFFFF", help="CTA text color hex")
    # thumbnail and variants
    parser.add_argument("--export-thumbnail", action="store_true", help="Export a thumbnail (frame at 1s)")
    parser.add_argument("--variants", default="", help="Comma-separated extra resolutions to export, e.g. 1280x720,1600x900")

    # reparse to include the newly added options
    args = parser.parse_args()

    ensure_dirs()
    engine, SessionLocal = setup_db("sqlite:///./backend/samples/mock_flow.db")
    campaign_id = create_campaign(SessionLocal, "https://example.com", "local-user")

    # compute target resolution
    try:
        w_str, h_str = args.resolution.split("x")
        target_resolution = (int(w_str), int(h_str))
    except Exception:
        target_resolution = (1920, 1080)

    install_fakes(target_resolution)
    install_redis_and_job_stubs()

    print("Running mocked pipeline for campaign:", campaign_id)
    result = jobs.generate_ad(campaign_id, url="https://example.com", user_id="local-user", job_id="manual")
    print("Result:", result)

    # copy artifacts to backend/samples/<campaign_id>/
    src_dir = Path(f"/tmp/creoAd_jobs/{campaign_id}")
    dest_dir = Path("backend/samples") / campaign_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    for f in src_dir.glob("*"):
        try:
            dest = dest_dir / f.name
            dest.write_bytes(f.read_bytes())
        except Exception:
            pass

    # prepare colors and sizes from args
    def _hex_to_rgb_tuple(hexstr, fallback=(255, 255, 255, 255)):
        try:
            h = hexstr.lstrip("#")
            if len(h) == 6:
                r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                return (r, g, b, 255)
            if len(h) == 8:
                r, g, b, a = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16)
                return (r, g, b, a)
        except Exception:
            return fallback

    headline_color = _hex_to_rgb_tuple(getattr(args, 'headline_color', '#FFFFFF'))
    value_color = _hex_to_rgb_tuple(getattr(args, 'value_color', '#E6E6E6'))
    cta_box_color = _hex_to_rgb_tuple(getattr(args, 'cta_box_color', '#FF5A00'))
    cta_text_color = _hex_to_rgb_tuple(getattr(args, 'cta_text_color', '#FFFFFF'))

    # Overlay HOOK -> VALUE -> CTA text onto images and produce an overlayed video
    try:
        script_path = src_dir / "script.json"
        if script_path.exists():
            import json
            from PIL import Image, ImageDraw, ImageFont

            script = json.loads(script_path.read_text())
            scenes = script.get("scenes", [])
            overlay_dir = src_dir / "overlay"
            overlay_dir.mkdir(exist_ok=True)

            # load a default font with sizes from args
            try:
                font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", args.headline_size)
                font_mid = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", args.value_size)
                font_cta = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", args.cta_size)
            except Exception:
                font_large = ImageFont.load_default()
                font_mid = ImageFont.load_default()
                font_cta = ImageFont.load_default()

            for i, s in enumerate(scenes):
                img_path = src_dir / f"scene_{i:02d}.png"
                if not img_path.exists():
                    continue
                img = Image.open(img_path).convert("RGBA")
                # resize to requested target resolution if different
                if (img.width, img.height) != target_resolution:
                    img = img.resize(target_resolution, resample=Image.LANCZOS)
                draw = ImageDraw.Draw(img)
                w, h = img.size

                # Hook (headline) - top (allow color customization via args)
                hook = s.get("text") or s.get("description") or ""
                hook = (hook[:80] + "...") if len(hook) > 80 else hook
                draw.text((w * 0.05, h * 0.05), hook, font=font_large, fill=headline_color)

                # Value - center
                value = script.get("narration", "")
                value = (value[:120] + "...") if len(value) > 120 else value
                draw.text((w * 0.05, h * 0.45), value, font=font_mid, fill=value_color)

                # CTA - bottom-right with simple box
                cta_override = args.cta_text
                cta = script.get("music_suggestion", "Try Free")
                cta_text = cta_override if cta_override is not None else ("Try Free Today" if not cta else cta)
                # compute CTA text size robustly
                try:
                    cta_w, cta_h = font_cta.getsize(cta_text)
                except Exception:
                    try:
                        bbox = draw.textbbox((0, 0), cta_text, font=font_cta)
                        cta_w = bbox[2] - bbox[0]
                        cta_h = bbox[3] - bbox[1]
                    except Exception:
                        cta_w, cta_h = (200, 50)
                box_pad = 20
                box_x = w - cta_w - box_pad * 2 - int(w * 0.05)
                box_y = h - cta_h - box_pad * 2 - int(h * 0.05)
                # semi-transparent box
                draw.rectangle([box_x, box_y, box_x + cta_w + box_pad * 2, box_y + cta_h + box_pad * 2], fill=cta_box_color)
                draw.text((box_x + box_pad, box_y + box_pad), cta_text, font=font_cta, fill=cta_text_color)

                out_img = overlay_dir / f"scene_{i:02d}.png"
                img.convert("RGB").save(out_img, format="PNG")

            # assemble overlay video using ffmpeg
            overlay_out = src_dir / "final_ad_overlay.mp4"
            per_frame = scenes[0].get("duration", 6) if scenes else 6
            img_pattern = str(overlay_dir / "scene_%02d.png")
            cmd = [
                "ffmpeg",
                "-y",
                "-framerate",
                f"1/{per_frame}",
                "-i",
                img_pattern,
                "-i",
                str(src_dir / "voice_with_music.wav"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-shortest",
                str(overlay_out),
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # copy overlay video to samples folder
            try:
                dest_ov = dest_dir / "final_ad_overlay.mp4"
                dest_ov.write_bytes(overlay_out.read_bytes())
            except Exception:
                pass
            print("Overlay video created at:", overlay_out)
            # export thumbnail if requested
            if getattr(args, "export_thumbnail", False):
                thumb_path = dest_dir / "thumbnail.jpg"
                # use ffmpeg to capture 1s frame
                try:
                    cmd2 = ["ffmpeg", "-y", "-ss", "1", "-i", str(overlay_out), "-frames:v", "1", str(thumb_path)]
                    subprocess.run(cmd2, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print("Thumbnail exported:", thumb_path)
                except Exception:
                    pass

            # export variant resolutions
            variants_str = getattr(args, "variants", "")
            if variants_str:
                for v in [r.strip() for r in variants_str.split(",") if r.strip()]:
                    try:
                        vw, vh = [int(x) for x in v.split("x")]
                    except Exception:
                        continue
                    variant_out = dest_dir / f"final_ad_{vw}x{vh}.mp4"
                    cmdv = [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(overlay_out),
                        "-vf",
                        f"scale={vw}:{vh}",
                        "-c:v",
                        "libx264",
                        "-crf",
                        "23",
                        "-preset",
                        "veryfast",
                        str(variant_out),
                    ]
                    try:
                        subprocess.run(cmdv, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        print("Variant exported:", variant_out)
                    except Exception:
                        pass
    except Exception as e:
        print("Overlay step failed:", e)

    print("Artifacts copied to:", dest_dir)


if __name__ == "__main__":
    run()
