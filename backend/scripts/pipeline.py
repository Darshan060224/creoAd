#!/usr/bin/env python3
"""End-to-end local ad pipeline.

Stages:
1) Scrape URL (Playwright + BeautifulSoup)
2) Generate JSON ad script (Ollama)
3) Generate scene images (ComfyUI API)
4) Generate narration (Chatterbox)
5) Assemble TV/Laptop/Mobile outputs (FFmpeg)
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import subprocess
import uuid
import shutil
import time
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import urllib.request
import websocket

from config import settings

from agents.brand import analyze_brand
from agents.creative_director import create_brief
from agents.copywriter import write_script
from agents.storyboard import build_storyboard
from agents.prompt_engineer import optimize_prompts
from agents.reviewer import eval_asset, rex_repair

try:
    from modules.script_generator import resolve_ollama_model
except Exception:
    resolve_ollama_model = None


OUTPUT_DIR = Path("backend/creoad_output")
IMAGES_DIR = OUTPUT_DIR / "images"
AUDIO_DIR = OUTPUT_DIR / "audio"
FINAL_DIR = OUTPUT_DIR / "final"
SCRIPT_PATH = OUTPUT_DIR / "script.json"

COMFY_SERVER = os.getenv("COMFY_SERVER", "127.0.0.1:8188")
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://localhost:11434")
CLIENT_ID = str(uuid.uuid4())


def ensure_dirs() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)


def preflight_checks(music_path: str) -> None:
    """Fail fast with clear messages if required local services/tools are missing."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH")

    music = Path(music_path)
    if not music.exists():
        raise RuntimeError(f"Music file not found: {music_path}")

    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        r.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Ollama not reachable at {OLLAMA_BASE}: {e}")

    try:
        r = requests.get(f"http://{COMFY_SERVER}/api/history/does-not-exist", timeout=5)
        # Any HTTP response means service is reachable.
        _ = r.status_code
    except Exception as e:
        raise RuntimeError(f"ComfyUI not reachable at http://{COMFY_SERVER}: {e}")


def scrape_url(url: str) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright
    from bs4 import BeautifulSoup

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, timeout=20000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")
    desc = soup.find("meta", {"name": "description"})
    return {
        "name": title.text.strip() if title and title.text else "Brand",
        "tagline": desc["content"].strip() if desc and desc.get("content") else "",
        "url": url,
    }


def _cleanup_gpu_memory() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def generate_script(brand_data: dict[str, Any], model: str | None = None) -> dict[str, Any]:
    selected_model = model or (resolve_ollama_model() if resolve_ollama_model else getattr(settings, "ollama_model", "llama3.2:3b"))
    prompt = f"""You are an expert TV ad copywriter.
Write a 30-second TV ad script for this business:
Name: {brand_data['name']}
Tagline: {brand_data['tagline']}
URL: {brand_data['url']}

Return ONLY valid JSON with this structure:
{{
  "headline": "main headline text",
  "scenes": [
    {{"id": 1, "duration": 6, "visual": "describe the scene visually",
      "narration": "what the voiceover says", "text_overlay": "on-screen text"}},
    ... 5 scenes total
  ],
  "cta": "call to action text"
}}"""

    r = requests.post(
        f"{OLLAMA_BASE}/api/generate",
        json={
            "model": selected_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", str(getattr(settings, "ollama_num_predict", 300)))),
                "temperature": float(os.getenv("OLLAMA_TEMPERATURE", str(getattr(settings, "ollama_temperature", 0.7)))),
                "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", str(getattr(settings, "ollama_num_ctx", 2048)))),
                "num_gpu": 1 if getattr(settings, "ollama_gpu", True) else 0,
            },
            "format": "json",
        },
        timeout=int(getattr(settings, "ollama_request_timeout", 60)),
    )
    r.raise_for_status()
    raw = r.json().get("response", "")
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError("Ollama response did not contain JSON")
    return json.loads(raw[start:end])


def queue_comfy_prompt(workflow: dict[str, Any]) -> str:
    payload = json.dumps({"prompt": workflow, "client_id": CLIENT_ID}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{COMFY_SERVER}/api/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["prompt_id"]


def wait_for_comfy_image(prompt_id: str) -> bytes:
    ws = websocket.WebSocket()
    ws.connect(f"ws://{COMFY_SERVER}/ws?clientId={CLIENT_ID}")
    try:
        while True:
            msg = json.loads(ws.recv())
            if msg.get("type") == "executing":
                data = msg.get("data", {})
                if data.get("node") is None and data.get("prompt_id") == prompt_id:
                    break
    finally:
        ws.close()

    with urllib.request.urlopen(f"http://{COMFY_SERVER}/api/history/{prompt_id}", timeout=30) as r:
        history = json.loads(r.read())

    filename = history[prompt_id]["outputs"]["9"]["images"][0]["filename"]
    with urllib.request.urlopen(f"http://{COMFY_SERVER}/api/view?filename={filename}", timeout=30) as r:
        return r.read()


def get_sdxl_workflow(
    prompt_text: str,
    width: int,
    height: int,
    seed: int = 42,
    steps: int = 20,
    cfg: float = 7.5,
    sampler_name: str = "euler",
    negative_prompt: str = "",
) -> dict[str, Any]:
    template_path = Path("backend/scripts/sdxl_template.json")
    workflow = json.loads(template_path.read_text())
    workflow["3"]["inputs"]["seed"] = seed
    workflow["3"]["inputs"]["steps"] = steps
    workflow["3"]["inputs"]["cfg"] = cfg
    workflow["3"]["inputs"]["sampler_name"] = sampler_name
    workflow["5"]["inputs"]["width"] = width
    workflow["5"]["inputs"]["height"] = height
    workflow["6"]["inputs"]["text"] = f"{prompt_text}, photorealistic, professional advertisement, 4k"
    workflow["7"]["inputs"]["text"] = negative_prompt or "blurry, ugly, watermark, text, logo, nsfw, low quality, distorted, cartoon"
    return workflow


def generate_scene_image(
    scene: dict[str, Any],
    index: int,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    sampler_name: str,
) -> str:
    workflow = get_sdxl_workflow(
        scene.get("visual_prompt", scene.get("visual", "clean product shot")),
        width=width,
        height=height,
        seed=42 + index,
        steps=steps,
        cfg=cfg,
        sampler_name=sampler_name,
        negative_prompt=scene.get("negative_prompt", ""),
    )
    prompt_id = queue_comfy_prompt(workflow)
    img_bytes = wait_for_comfy_image(prompt_id)
    out_path = IMAGES_DIR / f"scene_{index:02d}.png"
    out_path.write_bytes(img_bytes)
    return str(out_path)


def generate_voice(scenes: list[dict[str, Any]], out_path: str, turbo: bool = True, device: str = "cuda") -> str:
    import torchaudio as ta
    import torch

    full_narration = " ".join(s.get("narration", "") for s in scenes).strip()
    if not full_narration:
        full_narration = "Welcome to CreoAd. Discover your brand advantage today."

    if turbo:
        from chatterbox.tts_turbo import ChatterboxTurboTTS

        model = ChatterboxTurboTTS.from_pretrained(device=device)
        scene_texts = [s.get("narration", "").strip() for s in scenes if s.get("narration", "").strip()]
        if not scene_texts:
            scene_texts = [full_narration]

        def gen_chunk(text: str):
            with torch.inference_mode():
                return model.generate(text, audio_prompt_path=None)

        with ThreadPoolExecutor(max_workers=min(3, len(scene_texts))) as ex:
            wavs = list(ex.map(gen_chunk, scene_texts))

        combined = wavs[0] if len(wavs) == 1 else torch.cat(wavs, dim=-1)

        ta.save(out_path, combined, model.sr)
        return out_path

    from chatterbox.tts import ChatterboxTTS

    model = ChatterboxTTS.from_pretrained(device=device)
    wav = model.generate(full_narration, exaggeration=0.5, cfg_weight=0.5)
    ta.save(out_path, wav, model.sr)
    return out_path


def render_with_ffmpeg(
    image_paths: list[str],
    voice_path: str,
    music_path: str,
    headline: str,
    cta: str,
    out_path: str,
    width: int,
    height: int,
    v_bitrate: str,
    a_bitrate: str,
    a_rate: int,
    profile: str,
    level: str | None = None,
    maxrate: str | None = None,
    bufsize: str | None = None,
) -> None:
    # Build concat manifest (6s per scene)
    filelist = OUTPUT_DIR / "filelist.txt"
    with filelist.open("w") as f:
        for img in image_paths:
            f.write(f"file '{Path(img).resolve()}'\n")
            f.write("duration 6\n")
        if image_paths:
            # concat demuxer expects final file repeated
            f.write(f"file '{Path(image_paths[-1]).resolve()}'\n")

    safe_headline = headline.replace("'", "\\\\'")
    safe_cta = cta.replace("'", "\\\\'")

    vf = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{safe_headline}':fontsize=56:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2:"
        f"x=(w-text_w)/2:y=80:enable='between(t,0.5,5.5)',"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"text='{safe_cta}':fontsize=36:fontcolor=yellow:"
        f"x=(w-text_w)/2:y=h-90:enable='between(t,3,6)',"
        f"format=yuv420p[v];"
        f"[1:a]volume=1.0[voice];"
        f"[2:a]volume=0.25,atrim=0:30[music];"
        f"[voice][music]amix=inputs=2:duration=first[a]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(filelist),
        "-i",
        voice_path,
        "-i",
        music_path,
        "-filter_complex",
        vf,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        settings.ffmpeg_encoder,
        "-profile:v",
        profile,
    ]

    if settings.ffmpeg_encoder == "h264_nvenc":
        cmd[cmd.index(settings.ffmpeg_encoder) + 1:cmd.index(settings.ffmpeg_encoder) + 1] = ["-preset", "p1", "-rc", "vbr", "-cq", "23"]
    else:
        cmd[cmd.index(settings.ffmpeg_encoder) + 1:cmd.index(settings.ffmpeg_encoder) + 1] = ["-preset", settings.ffmpeg_preset, "-crf", "23"]

    if level:
        cmd.extend(["-level:v", level])

    cmd.extend([
        "-b:v",
        v_bitrate,
    ])

    if maxrate:
        cmd.extend(["-maxrate", maxrate])
    if bufsize:
        cmd.extend(["-bufsize", bufsize])

    cmd.extend([
        "-r",
        "30",
        "-c:a",
        "aac",
        "-b:a",
        a_bitrate,
        "-ar",
        str(a_rate),
        "-ac",
        "2",
        "-movflags",
        "+faststart",
        "-pix_fmt",
        "yuv420p",
        out_path,
    ])
    subprocess.run(cmd, check=True)


def assemble_video(
    image_paths: list[str],
    voice_path: str,
    music_path: str,
    script: dict[str, Any],
    fmt: str,
) -> str:
    specs = {
        "tv": {
            "w": 1920,
            "h": 1080,
            "vb": "5000k",
            "ab": "192k",
            "ar": 48000,
            "profile": "high",
            "level": "4.1",
            "maxrate": "8000k",
            "bufsize": "10000k",
        },
        "laptop": {
            "w": 1280,
            "h": 720,
            "vb": "2500k",
            "ab": "128k",
            "ar": 44100,
            "profile": "main",
            "level": None,
            "maxrate": None,
            "bufsize": None,
        },
        "mobile": {
            "w": 1080,
            "h": 1920,
            "vb": "3000k",
            "ab": "128k",
            "ar": 44100,
            "profile": "main",
            "level": None,
            "maxrate": None,
            "bufsize": None,
        },
        "square": {
            "w": 1080,
            "h": 1080,
            "vb": "3000k",
            "ab": "128k",
            "ar": 44100,
            "profile": "main",
            "level": None,
            "maxrate": None,
            "bufsize": None,
        },
    }
    if fmt not in specs:
        raise ValueError(f"Unsupported format: {fmt}")
    s = specs[fmt]
    out = FINAL_DIR / f"creoad_ad_{fmt}.mp4"

    render_with_ffmpeg(
        image_paths=image_paths,
        voice_path=voice_path,
        music_path=music_path,
        headline=script.get("headline", "Your Brand Here"),
        cta=script.get("cta", "Visit us today"),
        out_path=str(out),
        width=s["w"],
        height=s["h"],
        v_bitrate=s["vb"],
        a_bitrate=s["ab"],
        a_rate=s["ar"],
        profile=s["profile"],
        level=s["level"],
        maxrate=s["maxrate"],
        bufsize=s["bufsize"],
    )
    return str(out)


def run_pipeline(
    url: str,
    formats: list[str],
    model: str,
    music_path: str,
    device: str,
    turbo: bool,
    comfy_resolution: str | None = None,
    framework: str = "AIDA",
) -> None:
    preflight_checks(music_path)
    ensure_dirs()

    job_id = str(uuid.uuid4())

    print(f"[1/5] Scraping {url}...")
    brand_raw = scrape_url(url)
    # inject url for compatibility
    brand_raw["url"] = url

    print("[2/5] Running 6-Agent Pipeline...")
    t2 = time.time()
    print("  -> BRAND ANALYST analyzing brand...")
    brand_profile = analyze_brand(brand_raw, job_id)

    print("  -> CREATIVE DIRECTOR creating brief...")
    creative_brief = create_brief(brand_profile, job_id)
    creative_brief["ad_framework"] = framework

    print(f"  -> COPYWRITER writing script using {framework}...")
    duration = 30
    script = write_script(brand_profile, creative_brief, duration, job_id)

    print("  -> QUALITY REVIEWER (EVAL & REX) checking script...")
    eval_result = eval_asset("script", script, creative_brief)
    if eval_result.get("score", 10) < 8.0:
        print(f"  -> REX REPAIR triggered (Score: {eval_result.get('score')}) -> fixing script...")
        script = rex_repair("script", script, eval_result.get("feedback", "Low score"), creative_brief)

    print("  -> STORYBOARD + PROMPT ENGINEER optimizing scenes...")
    storyboard = build_storyboard(script, creative_brief)
    optimized = optimize_prompts(storyboard["scenes"], creative_brief)
    script["scenes"] = optimized

    with open(OUTPUT_DIR / "brand_profile.json", "w") as f:
        json.dump(brand_profile, f, indent=2)
    with open(OUTPUT_DIR / "creative_brief.json", "w") as f:
        json.dump(creative_brief, f, indent=2)
    SCRIPT_PATH.write_text(json.dumps(script, indent=2))
    _cleanup_gpu_memory()

    print("[3/5] Generating scene images with ComfyUI...")
    comfy_micro = {
        "tv": {"w": 1024, "h": 576, "steps": 4, "cfg": 1.5, "sampler": "euler"},
        "laptop": {"w": 1024, "h": 576, "steps": 4, "cfg": 1.5, "sampler": "euler"},
        "mobile": {"w": 1024, "h": 576, "steps": 4, "cfg": 1.5, "sampler": "euler"},
        "square": {"w": 1024, "h": 576, "steps": 4, "cfg": 1.5, "sampler": "euler"},
    }
    base_fmt = formats[0] if formats and formats[0] in comfy_micro else "tv"
    cm = comfy_micro[base_fmt]

    # Optional override to generate all scenes at one fixed Comfy resolution
    # while still exporting to multiple target formats via FFmpeg.
    if comfy_resolution:
        try:
            cw, ch = [int(x) for x in comfy_resolution.lower().split("x")]
            cm = {
                "w": cw,
                "h": ch,
                "steps": cm["steps"],
                "cfg": cm["cfg"],
                "sampler": cm["sampler"],
            }
        except Exception:
            pass
    image_paths = [None] * len(script["scenes"])
    with ThreadPoolExecutor(max_workers=min(5, len(script["scenes"]) or 1)) as executor:
        future_map = {
            executor.submit(
                generate_scene_image,
                s,
                i,
                width=cm["w"],
                height=cm["h"],
                steps=cm["steps"],
                cfg=cm["cfg"],
                sampler_name=cm["sampler"],
            ): i
            for i, s in enumerate(script["scenes"])
        }
        for future in as_completed(future_map):
            image_paths[future_map[future]] = future.result()
    _cleanup_gpu_memory()

    print("[4/5] Generating voiceover with Chatterbox...")
    voice_path = str(AUDIO_DIR / "voice.wav")
    generate_voice(script["scenes"], voice_path, turbo=turbo, device=device)
    _cleanup_gpu_memory()

    print("[5/5] Assembling videos with FFmpeg...")
    with ThreadPoolExecutor(max_workers=min(len(formats), 4) or 1) as executor:
        future_map = {executor.submit(assemble_video, image_paths, voice_path, music_path, script, fmt): fmt for fmt in formats}
        for future in as_completed(future_map):
            fmt = future_map[future]
            out = future.result()
            print(f"  -> {fmt}: {out}")
    _cleanup_gpu_memory()

    print(f"Done. Artifacts saved to {OUTPUT_DIR}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CreoAd full local pipeline runner")
    parser.add_argument("url_pos", nargs="?", help="Business URL (positional shortcut)")
    parser.add_argument("--url", required=False, help="Business URL")
    parser.add_argument("--formats", default="tv,laptop,mobile", help="Comma-separated formats")
    parser.add_argument("--ollama-model", default=os.getenv("OLLAMA_MODEL", getattr(settings, "ollama_model", "llama3.2:3b")), help="Ollama model")
    parser.add_argument("--music", default="backend/assets/music/track_01.mp3", help="Background music path")
    parser.add_argument("--device", default="cuda", help="Chatterbox device: cuda or cpu")
    parser.add_argument("--no-turbo", action="store_true", help="Use standard ChatterboxTTS instead of turbo")
    parser.add_argument(
        "--comfy-resolution",
        default=None,
        help="Optional fixed Comfy generation resolution (e.g. 1920x1080) independent of output formats",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    url = args.url or args.url_pos
    if not url:
        raise SystemExit("Provide a URL via --url or positional arg, e.g. pipeline.py https://example.com")
    formats = [x.strip() for x in args.formats.split(",") if x.strip()]
    run_pipeline(
        url=url,
        formats=formats,
        model=args.ollama_model,
        music_path=args.music,
        device=args.device,
        turbo=not args.no_turbo,
        comfy_resolution=args.comfy_resolution,
        framework="AIDA",
    )
