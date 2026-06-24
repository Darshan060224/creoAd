# Quick Start - Local (No Docker)

This guide runs the full stack directly on your machine.

## Stages Covered

- Stage A Scraper: Lightpanda browser, Playwright, BeautifulSoup4, Cloudflare Browser Rendering API
- Stage B1 LLM: Ollama with llama3.1:8b, mistral:7b, qwen2.5:7b, deepseek-r1:7b
- Stage B2 Images: ComfyUI + SDXL
- Stage B3 Voiceover: Coqui TTS + Chatterbox
- Stage B4 Music: local royalty-free files
- Stage C Video: FFmpeg, MoviePy, Pillow, OpenCV, optional Remotion in frontend
- Queue + Storage + Backend: Redis + RQ/Celery, MinIO, Postgres + SQLAlchemy, FastAPI + Next.js

## 1) Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg redis-server postgresql postgresql-contrib git curl
```

Start and enable local services:

```bash
sudo systemctl enable --now redis-server
sudo systemctl enable --now postgresql
```

Create Postgres DB/user:

```bash
sudo -u postgres psql -c "CREATE USER creouser WITH PASSWORD 'darshan24';"
sudo -u postgres psql -c "CREATE DATABASE creoAd_db OWNER creouser;"
```

## 2) Python Backend Setup

```bash
cd /home/da24/Desktop/creoAd
source .venv/bin/activate
pip install -r backend/requirements.txt
playwright install chromium
```

## 3) Node Frontend Setup

```bash
cd /home/da24/Desktop/creoAd/frontend
npm install
```

## 4) MinIO (Local S3)

Download MinIO binary and run locally:

```bash
mkdir -p /home/da24/Desktop/creoAd/.local/minio-data
minio server /home/da24/Desktop/creoAd/.local/minio-data --console-address ":9001"
```

Default app values in this repo expect:

- endpoint: localhost:9000
- access key: creoad
- secret key: creoad123

## 5) Ollama + Models

Install Ollama, run service, then pull models:

```bash
ollama serve
ollama pull llama3.1:8b
ollama pull mistral:7b
ollama pull qwen2.5:7b
ollama pull deepseek-r1:7b
```

## 6) ComfyUI + SDXL

Run local ComfyUI and place SDXL checkpoint in your model path.
Set backend config/env to use:

- COMFYUI_URL=http://localhost:8188
- COMFYUI_CHECKPOINT=<your_sdxl_checkpoint_name>

## 7) Chatterbox + Coqui TTS

Coqui is installed via backend requirements.
Chatterbox installs from GitHub via backend requirements.

Optional env for voice selection:

```bash
export VOICE_BACKEND=chatterbox
export CHATTERBOX_DEVICE=cpu
export COQUI_TTS_MODEL=tts_models/en/ljspeech/tacotron2-DDC
```

## 7.1) Bootstrap Local Music Assets (Stage B4)

Create starter local tracks so B4 works out of the box:

```bash
cd /home/da24/Desktop/creoAd
source .venv/bin/activate
python backend/scripts/bootstrap_music_assets.py
```

Optional override:

```bash
export LOCAL_MUSIC_DIR=/home/da24/Desktop/creoAd/backend/assets/music
```

## 8) Environment Variables

Create or update backend env:

```bash
cat > /home/da24/Desktop/creoAd/backend/.env << 'EOF'
DATABASE_URL=postgresql://creouser:darshan24@localhost:5432/creoAd_db
REDIS_URL=redis://localhost:6379
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=creoad
MINIO_SECRET_KEY=creoad123
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
COMFYUI_URL=http://localhost:8188
VOICE_BACKEND=chatterbox
CHATTERBOX_DEVICE=cpu
COQUI_TTS_MODEL=tts_models/en/ljspeech/tacotron2-DDC
EOF
```

## 9) Run Backend + Worker + Frontend

Terminal 1:

```bash
cd /home/da24/Desktop/creoAd/backend
source /home/da24/Desktop/creoAd/.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2:

```bash
cd /home/da24/Desktop/creoAd/backend
source /home/da24/Desktop/creoAd/.venv/bin/activate
rq worker ad_jobs video_jobs --with-scheduler
```

Terminal 3:

```bash
cd /home/da24/Desktop/creoAd/frontend
npm run dev
```

## 10) Verify

```bash
curl http://localhost:8000/health
```

Open:

- frontend: http://localhost:3000
- backend docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001

## Notes

- Lightpanda is not a Python package in backend requirements; integrate it as a standalone browser runtime/client where you run scraping agents.
- Cloudflare Browser Rendering API is HTTP API based; use with requests/httpx and your Cloudflare credentials.
- Remotion is optional for advanced React-based rendering, while current backend pipeline already assembles MP4s with FFmpeg.

## Smoke Test

Run one integration smoke test for pipeline stage transitions (Redis + PostgreSQL):

```bash
cd /home/da24/Desktop/creoAd
source .venv/bin/activate
pytest -q backend/tests/test_pipeline_smoke.py
```
