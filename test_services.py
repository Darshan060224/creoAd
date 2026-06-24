#!/usr/bin/env python3
"""
CreoAd Service Health Check
Tests: Ollama, ComfyUI, Redis, PostgreSQL, MinIO, FFmpeg
"""

import subprocess
import sys

RESET  = "\033[0m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"

def ok(msg):  print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg): print(f"  {RED}❌ {msg}{RESET}")
def warn(msg): print(f"  {YELLOW}⚠️  {msg}{RESET}")
def section(title): print(f"\n{BOLD}{CYAN}{'─'*50}\n  {title}\n{'─'*50}{RESET}")

results = {}

# ── Ollama ──────────────────────────────────────────────
section("1 · Ollama  (port 11434)")
try:
    import requests
    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    if r.status_code == 200:
        models = r.json().get("models", [])
        names  = [m["name"] for m in models]
        ok(f"Ollama online — models: {names or 'none pulled yet'}")
        results["ollama"] = "✅"
    else:
        fail(f"Unexpected status {r.status_code}")
        results["ollama"] = "❌"
except Exception as e:
    fail(f"Ollama offline — {e}")
    results["ollama"] = "❌"

# ── ComfyUI ─────────────────────────────────────────────
section("2 · ComfyUI  (port 8188)")
try:
    import requests
    r = requests.get("http://localhost:8188/system_stats", timeout=5)
    if r.status_code == 200:
        data = r.json()
        gpu  = data.get("devices", [{}])[0] if data.get("devices") else {}
        ok(f"ComfyUI online — GPU: {gpu.get('name', 'N/A')}")
        results["comfyui"] = "✅"
    else:
        fail(f"Unexpected status {r.status_code}")
        results["comfyui"] = "❌"
except Exception as e:
    fail(f"ComfyUI offline — {e}")
    results["comfyui"] = "❌"

# ── Redis ────────────────────────────────────────────────
section("3 · Redis  (port 6379)")
try:
    import redis
    r = redis.Redis(host="localhost", port=6379, socket_connect_timeout=3)
    pong = r.ping()
    if pong:
        ok(f"Redis online — PONG received")
        results["redis"] = "✅"
    else:
        fail("No PONG")
        results["redis"] = "❌"
except Exception as e:
    fail(f"Redis offline — {e}")
    results["redis"] = "❌"

# ── Database (auto-detect SQLite vs PostgreSQL) ─────────────
section("4 · Database")
try:
    import os, pathlib
    # Read DATABASE_URL from .env or environment
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        env_file = pathlib.Path(__file__).parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.strip().startswith("DATABASE_URL="):
                    db_url = line.split("=", 1)[1].strip()
                    break
    if not db_url:
        db_url = "sqlite:///./creoAd.db"

    if db_url.startswith("sqlite"):
        # SQLite — just check the file exists and is readable
        db_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
        if not db_path.startswith("/"):
            db_path = str(pathlib.Path(__file__).parent / db_path.lstrip("./"))
        if pathlib.Path(db_path).exists():
            size_kb = pathlib.Path(db_path).stat().st_size // 1024
            ok(f"SQLite online — {db_path} ({size_kb}KB)")
            results["postgres"] = "✅"
        else:
            fail(f"SQLite file not found: {db_path}")
            results["postgres"] = "❌"
    else:
        # PostgreSQL
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="creoad123",
            dbname="postgres",
            connect_timeout=5,
        )
        cur = conn.cursor()
        cur.execute("SELECT version();")
        ver = cur.fetchone()[0].split(",")[0]
        conn.close()
        ok(f"PostgreSQL online — {ver}")
        results["postgres"] = "✅"
except Exception as e:
    fail(f"Database offline — {e}")
    results["postgres"] = "❌"

# ── MinIO ────────────────────────────────────────────────
section("5 · MinIO  (port 9000 / console 9001)")
try:
    from minio import Minio
    client = Minio(
        "localhost:9000",
        access_key="creoad",
        secret_key="creoad123",
        secure=False,
    )
    buckets = list(client.list_buckets())
    names   = [b.name for b in buckets]
    ok(f"MinIO online — buckets: {names or 'none yet'}")
    results["minio"] = "✅"
except Exception as e:
    fail(f"MinIO offline — {e}")
    results["minio"] = "❌"

# ── FFmpeg ───────────────────────────────────────────────
section("6 · FFmpeg  (system binary)")
try:
    proc = subprocess.run(
        ["ffmpeg", "-version"],
        capture_output=True, text=True, timeout=10
    )
    first_line = proc.stdout.splitlines()[0] if proc.stdout else ""
    if "ffmpeg version" in first_line:
        ok(first_line)
        results["ffmpeg"] = "✅"
    else:
        fail("ffmpeg not found or unexpected output")
        results["ffmpeg"] = "❌"
except Exception as e:
    fail(f"FFmpeg error — {e}")
    results["ffmpeg"] = "❌"

# ── Summary ──────────────────────────────────────────────
section("SUMMARY")
labels = {
    "ollama":   "Ollama   (11434)",
    "comfyui":  "ComfyUI  (8188) ",
    "redis":    "Redis    (6379) ",
    "postgres": "Postgres (5432) ",
    "minio":    "MinIO    (9000) ",
    "ffmpeg":   "FFmpeg   (bin)  ",
}
all_ok = True
for key, label in labels.items():
    status = results.get(key, "❓")
    print(f"  {status}  {label}")
    if status != "✅":
        all_ok = False

print()
if all_ok:
    print(f"  {GREEN}{BOLD}All services healthy — ready to run CreoAd! 🚀{RESET}")
else:
    missing = [k for k, v in results.items() if v != "✅"]
    print(f"  {YELLOW}{BOLD}Services down: {', '.join(missing)}{RESET}")
    print(f"  {YELLOW}Run: docker-compose up -d   to start Docker services{RESET}")

print()
sys.exit(0 if all_ok else 1)
