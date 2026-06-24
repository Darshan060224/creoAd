# CreoAd - AI-Powered Ad Generation Platform

A complete local stack for generating professional 30-second video ads from business websites using AI and open-source tools.

## 🎯 Features

- **✍️ Intelligent Scraping** → Extract brand data from business URLs
- **🤖 AI Script Generation** → Create 5-scene ad scripts with Ollama (Llama 3.1 or Mistral)
- **🖼️ Image Generation** → Render scene images with ComfyUI (Stable Diffusion)
- **🎤 Voiceover Synthesis** → Generate natural-sounding narration with Coqui TTS
- **🎬 Video Assembly** → Combine everything with FFmpeg
- **✏️ Interactive Editing** → Edit text, voice, and music, then re-render
- **📊 Real-time Progress** → Track pipeline status with live updates

## 🏗️ Architecture

```
┌─────────────────┐
│   Next.js       │  Frontend (URL input, video preview, editor)
│  (Port 3000)    │
└────────┬────────┘
         │
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                        │
│                      (Port 8000)                            │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Scraper  │  │ Ollama   │  │ ComfyUI  │  │ Coqui    │   │
│  │ (Stage A)│  │ (Stage   │  │ (Stage   │  │ TTS      │   │
│  │          │  │ B1)      │  │ B2)      │  │ (B3)     │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ FFmpeg   │  │ Redis    │  │ Postgres │                 │
│  │ (Stage C)│  │ Queue    │  │ DB       │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Tech Stack

### Core Services (Docker)
- **Ollama** (11434) → LLM for script generation
- **ComfyUI** (8188) → Stable Diffusion for image generation
- **FastAPI** (8000) → Python backend API
- **Next.js** (3000) → React frontend
- **PostgreSQL** (5432) → Database
- **Redis** (6379) → Job queue + caching
- **MinIO** (9000/9001) → S3-compatible storage

### Local Tools
- **Coqui TTS** → Voice synthesis
- **FFmpeg** → Video assembly
- **Playwright** → Web scraping
- **BeautifulSoup** → HTML parsing

## 📋 Prerequisites

### System Requirements
- Docker & Docker Compose
- 8GB+ RAM (recommended 16GB for GPU)
- 50GB+ disk space
- Ubuntu/Debian/MacOS/Windows (WSL2)

### Optional: GPU Support (Oracle Cloud)
- NVIDIA GPU (A10 Instances recommended)
- nvidia-container-runtime

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd /home/da24/Desktop/creoAd

# Create .env file
cp .env.example .env

# Download Ollama models (optional - will auto-download if missing)
docker run -v ollama_data:/root/.ollama ollama/ollama ollama pull llama3.1:8b
docker run -v ollama_data:/root/.ollama ollama/ollama ollama pull mistral:7b
```

### 2. Start All Services

```bash
docker-compose up -d

# Wait for services to be ready (about 1-2 minutes)
docker-compose ps

# Check backend health
curl http://localhost:8000/health
```

### 3. Open Frontend

Navigate to **http://localhost:3000** in your browser.

### 4. Generate Your First Ad

1. Enter a business website URL
2. Watch the progress bar as it:
   - Scrapes the business info
   - Generates a 5-scene script
   - Creates images for each scene
   - Generates voiceover
   - Assembles the final MP4
3. Preview, edit, and download your ad!

## 📝 Full Build Order

### Stage A: Scraping (Backend: `modules/scraper.py`)
- Fetches business website
- Extracts: company name, tagline, products, industry, CTA
- Returns structured brand JSON

### Stage B1: Script Generation (Backend: `modules/script_generator.py`)
- Sends brand data to Ollama (Llama 3.1 or Mistral)
- Generates 5 scenes with:
  - Scene descriptions (for image generation)
  - On-screen text
  - Full voiceover narration
  - Music suggestion

### Stage B2: Image Generation (Backend: `modules/image_generator.py`)
- Sends each scene description to ComfyUI
- Uses Stable Diffusion SDXL (1280x720)
- Handles GPU/CPU rendering
- Fallback: placeholder images if GPU unavailable

### Stage B3: Voiceover (Backend: `modules/voice_generator.py`)
- Uses Coqui TTS for natural speech synthesis
- Options: female/male voices, different speeds
- Fallback: pyttsx3 or silent audio
- Outputs: WAV format (~7 seconds for 30s ad)

### Stage C: Video Assembly (Backend: `modules/video_assembler.py`)
- Combines images with fade transitions
- Mix voiceover + background music
- Encode to H.264 MP4
- Output: 1280x720 @30fps

### Stage D: Frontend & Editing
- React UI with real-time job polling
- VideoPreview: play, download, edit
- EditPanel: change text, voice, music
- Re-render: triggers new pipeline with edited content

## 🔧 Configuration

### Ollama Models (change in `config.py`)
```python
ollama_model: str = "llama3.1:8b"  # Options: mistral:7b, qwen2.5:7b
```

### Image Generation
- **High Quality**: SDXL (default, ~60 seconds per image)
- **Fast**: Stable Diffusion 1.5 (change in `image_generator.py`)

### Voiceover
- Coqui TTS (high quality, open source)
- pyttsx3 (fallback, doesn't need internet)

## 📊 Monitoring

### Real-time Progress
- Frontend polls `/api/job-status/{job_id}` every 2 seconds
- Redis stores stage progress
- PostgreSQL logs all stages

### View Logs
```bash
# Backend logs
docker-compose logs -f backend

# Worker logs
docker-compose logs -f worker

# All services
docker-compose logs -f
```

### Database
```bash
# Access PostgreSQL
docker-compose exec postgres psql -U creouser -d creoAd_db

# View campaigns
SELECT id, user_id, status, created_at FROM campaigns ORDER BY created_at DESC;
```

### Redis
```bash
# View job queue
docker-compose exec redis redis-cli
> KEYS job:*
> HGETALL job:YOUR_JOB_ID
```

## 🎨 Edit & Re-render

Users can edit after generation:

1. **Scene Text** - Change what appears on screen
2. **Voiceover** - Rewrite the full narration
3. **Background Music** - Choose from presets or upload
4. **Re-render** - Triggers a fast reprocessing

Re-render skips scraping/script generation, goes straight to image/audio/video assembly.

## 🔌 API Endpoints

```
POST   /api/generate-ad              → Start ad generation
GET    /api/job-status/{job_id}      → Poll job progress
GET    /api/campaign/{campaign_id}   → Get campaign details
POST   /api/campaign/{id}/edit-and-render  → Re-render with edits
GET    /api/user/{user_id}/campaigns  → List user's ads
```

## 🗂️ File Structure

```
creoAd/
├── docker-compose.yml              # Main orchestration
├── .env.example                    # Configuration template
├── README.md                       # This file
│
├── backend/                        # FastAPI application
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                    # FastAPI app + endpoints
│   ├── config.py                  # Configuration
│   ├── models.py                  # SQLAlchemy models
│   ├── schemas.py                 # Pydantic schemas
│   ├── jobs.py                    # RQ job orchestrator
│   └── modules/
│       ├── scraper.py             # Stage A
│       ├── script_generator.py     # Stage B1
│       ├── image_generator.py      # Stage B2
│       ├── voice_generator.py      # Stage B3
│       └── video_assembler.py      # Stage C
│
└── frontend/                       # Next.js application
    ├── Dockerfile
    ├── package.json
    ├── next.config.js
    ├── pages/
    │   └── index.js               # Main page
    ├── components/
    │   ├── GeneratorForm.js        # URL input form
    │   ├── JobMonitor.js           # Progress tracking
    │   ├── VideoPreview.js         # Video player + download
    │   └── EditPanel.js            # Edit & re-render UI
    └── styles/
        ├── Home.module.css
        ├── GeneratorForm.module.css
        ├── JobMonitor.module.css
        ├── VideoPreview.module.css
        └── EditPanel.module.css
```

## 🚨 Troubleshooting

### Services won't start
```bash
# Check Docker daemon
docker ps

# Clean up and restart
docker-compose down -v
docker-compose up -d
```

### Ollama taking too long
```bash
# Pre-pull models
docker-compose exec ollama ollama pull llama3.1:8b

# Check if running
curl http://localhost:11434/api/tags
```

### ComfyUI not generating images
```bash
# Check logs
docker-compose logs comfyui

# Make sure SDXL model is downloaded
# Models should be in comfyui_data/models/checkpoints/
```

### Out of memory errors
```bash
# Reduce model size
OLLAMA_MODEL=mistral:7b  # smaller than llama3.1:8b
# Or adjust ComfyUI settings for lower VRAM
```

### Video assembly fails
```bash
# Verify FFmpeg is installed in backend
docker-compose exec backend which ffmpeg

# Check audio files exist
docker-compose exec backend ls -la /tmp/creoAd_jobs/
```

## 🔐 Security Notes

- Change MinIO credentials in `.env` before production
- Use environment variables for sensitive data
- Database should be on private network only
- Consider adding authentication to FastAPI endpoints

## 📈 Performance Tips

### Single Machine (Development)
- Reduce image quality (lower `crf` value in FFmpeg)
- Use smaller Ollama model (mistral:7b)
- Limit ComfyUI resolution to 768x432

### Oracle Cloud (Production)
- Use GPU instance (VM.GPU.A10.1) for ComfyUI
- Deploy on High Memory instance (32GB+)
- Use object storage (Oracle Object Storage) instead of MinIO
- Add Redis Cluster for scaling

## 🤝 Contributing

To add new features:

1. **New scraper logic** → Edit `backend/modules/scraper.py`
2. **New LLM models** → Update `backend/config.py` and `script_generator.py`
3. **New image models** → Modify `image_generator.py` workflow
4. **New frontend components** → Add to `frontend/components/`

## 📄 License

MIT License - feel free to use for personal/commercial projects

## 🎓 Learning Resources

- Ollama: https://ollama.ai
- ComfyUI: https://github.com/comfyanonymous/ComfyUI
- Coqui TTS: https://github.com/coqui-ai/TTS
- FastAPI: https://fastapi.tiangolo.com
- Next.js: https://nextjs.org

---

**Ready to generate ads?** Run `docker-compose up -d` and visit http://localhost:3000!
