# 🏗️ Architecture & Implementation Details

Complete technical reference for CreoAd's AI ad generation pipeline.

## System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                      │
│                       Port 3000 - React                        │
├────────────────────────────────────────────────────────────────┤
│  GeneratorForm → JobMonitor → VideoPreview → EditPanel         │
│  (URL Input)   (Progress)   (Player)       (Tweaks)           │
└─────────────────────────────┬────────────────────────────────┘
                              │ HTTP/WebSocket
┌─────────────────────────────┼────────────────────────────────┐
│                   BACKEND API (FastAPI)                        │
│                    Port 8000 - Python                          │
├─────────────────────────────┼────────────────────────────────┤
│  Endpoints:                                                   │
│  POST   /api/generate-ad             → Enqueue Job            │
│  GET    /api/job-status/{id}         → Poll Progress          │
│  GET    /api/campaign/{id}           → Get Results            │
│  POST   /api/campaign/{id}/edit-and-render → Re-render       │
│  GET    /api/user/{id}/campaigns     → List Ads              │
└─────────────────────────────┬────────────────────────────────┘
                              │ Async Jobs
┌─────────────────────────────┼────────────────────────────────┐
│              PIPELINE ORCHESTRATION (RQ + Redis)              │
├─────────────────────────────┼────────────────────────────────┤
│  Job Queue: ad_jobs, video_jobs                              │
│  Worker Processes × N (can scale)                            │
└─────────────────────────────┬────────────────────────────────┘
        ┌─────────┬──────────┬──────────┬──────────┐
        ↓         ↓          ↓          ↓          ↓
   ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐ ┌────────┐
   │ Scrape │ │Script  │ │Images  │ │Voiceover│ │ Video  │
   │(BeautifulSoup) │(Ollama) │ (ComfyUI)│(Coqui) │(FFmpeg)│
   │        │ │        │ │        │ │         │ │        │
   │Stage A │ │Stage B1│ │Stage B2│ │ Stage B3 │ │Stage C │
   └────────┘ └────────┘ └────────┘ └─────────┘ └────────┘
```

## Data Flow

### 1. Initial Request (User Submits URL)

```
User Input
    ↓
Frontend (GeneratorForm)
    ↓
POST /api/generate-ad
    ↓
Backend (main.py)
    ├── Create Campaign record (Postgres)
    ├── Enqueue RQ job
    └── Return job_id + campaign_id
    ↓
Frontend polls /api/job-status/{job_id} every 2 seconds
    ↓
Shows progress bar (scrape → script → images → voice → video)
```

### 2. Pipeline Execution

```
Stage A: Scrape URL (modules/scraper.py)
    Input: Business URL
    Process:
        1. Fetch HTML with requests
        2. Parse with BeautifulSoup
        3. Extract: name, description, products, industry, CTA
    Output: brand_data JSON
    Logs: job_logs table + Redis hash
    ↓

Stage B1: Generate Script (modules/script_generator.py)
    Input: brand_data
    Process:
        1. Build prompt for Ollama
        2. Call Ollama API (http://ollama:11434/api/generate)
        3. Parse 5-scene JSON response
    Output: script_data (scenes[], narration, music_suggestion)
    Time: ~60-90 seconds on CPU
    ↓

Stage B2: Generate Images (modules/image_generator.py)
    Input: 5 scene descriptions from script_data
    Process:
        1. For each scene:
        2. Send to ComfyUI (workflow JSON)
        3. Poll for completion
        4. Save generated image
    Output: [scene_0.png, scene_1.png, ..., scene_4.png]
    Time: ~60-120 seconds per image (depends on GPU)
    Total: 5-10 minutes on GPU, 30+ minutes on CPU
    ↓

Stage B3: Generate Voiceover (modules/voice_generator.py)
    Input: Narration text from script_data
    Process:
        1. Call Coqui TTS CLI: `tts --text "..." --out_path output.wav`
        2. Generate natural speech audio
    Output: voiceover.wav
    Time: ~30-60 seconds
    Fallback: pyttsx3 or silent audio
    ↓

Stage C: Assemble Video (modules/video_assembler.py)
    Input: [scene images], voiceover.wav
    Process:
        1. Create concat demuxer file
        2. FFmpeg concat: images → video_no_audio.mp4
        3. FFmpeg mux: video + audio → final_ad.mp4
        4. Encode: H.264 @ 23 CRF (quality), 1280x720 @ 30fps
    Output: final_ad.mp4
    Time: ~3-5 minutes
    ↓

Update Campaign Status
    ├── Set status = "done"
    ├── Set video_url = "/videos/{campaign_id}/final.mp4"
    ├── Store scenes metadata
    └── Mark job as complete in Redis
    ↓

Frontend Detects Completion
    ├── Shows VideoPreview component
    ├── Plays video in player
    ├── Shows edit & download buttons
    └── Ready for re-render or download
```

## Database Schema

### campaigns table
```sql
CREATE TABLE campaigns (
    id UUID PRIMARY KEY,              -- UUIDv4
    user_id VARCHAR(255),             -- User identifier
    job_id VARCHAR(255),              -- RQ job ID
    business_url TEXT,                -- Input URL
    status VARCHAR(50),               -- queued|scraping|writing|generating|assembling|done|error
    
    -- Intermediate results
    brand_data JSONB,                 -- Scraped info
    script_data JSONB,                -- Generated script
    scenes_data JSONB,                -- Scene metadata + URLs
    
    -- Final output
    video_url TEXT,                   -- Path to MP4
    video_duration INTEGER,           -- Seconds
    
    -- Metadata
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    error_message TEXT                -- Error details if failed
);
```

### job_logs table
```sql
CREATE TABLE job_logs (
    id UUID PRIMARY KEY,
    campaign_id UUID FOREIGN KEY,
    job_id VARCHAR(255),              -- RQ job ID
    stage VARCHAR(50),                -- scrape|script|images|voice|video
    status VARCHAR(50),               -- running|success|error
    message TEXT,                     -- Log message
    duration_ms INTEGER,              -- How long this stage took
    created_at TIMESTAMP
);
```

## Module Details

### scraper.py (Stage A)

**Responsibility**: Extract brand information from HTML

**Algorithm**:
```
1. Fetch URL with requests (10s timeout)
2. Parse HTML with BeautifulSoup
3. Extract company name from: <title>, <h1>, og:title
4. Extract tagline from: meta description, <h2>, first <p>
5. Extract products from: <h3> tags, <li> tags
6. Classify industry via keyword matching
7. Find CTA button text
8. Return structured JSON
```

**Fallbacks**:
- If BeautifulSoup fails → Return empty defaults
- If URL unreachable → Log error, continue with placeholder

**Output**:
```json
{
  "company_name": "Acme Corp",
  "tagline": "The best services in town",
  "description": "We provide...",
  "products": ["Product A", "Product B"],
  "industry": "services|retail|finance|etc",
  "call_to_action": "Contact us today",
  "tone": "professional",
  "target_audience": "general"
}
```

### script_generator.py (Stage B1)

**Responsibility**: AI script generation using Ollama

**Algorithm**:
```
1. Format prompt with brand data
2. POST to http://ollama:11434/api/generate
3. LLM generates 5-scene JSON response
4. Parse and validate structure
5. Ensure each scene has: id, title, description, text, duration
6. Ensure narration is ~30-40 words
7. Return script JSON
```

**Model Selection**:
```
OLLAMA_MODEL=llama3.1:8b     # Default, best quality
           =mistral:7b       # Faster, lighter
           =qwen2.5:7b       # Multilingual
```

**Output**:
```json
{
  "scenes": [
    {
      "id": 0,
      "title": "Hook",
      "description": "Professional office with bustling employees...",
      "text": "Meet Acme Corp",
      "duration": 6
    },
    ...5 scenes total...
  ],
  "narration": "Your business needs a partner you can trust...",
  "music_suggestion": "upbeat, energetic"
}
```

### image_generator.py (Stage B2)

**Responsibility**: Generate scene images via ComfyUI

**Algorithm**:
```
1. For each scene description:
   a. Build ComfyUI workflow JSON
   b. POST to http://comfyui:8188/prompt
   c. Get prompt_id
   d. Poll /history/{prompt_id} until complete
   e. Save generated image
2. Fallback: Create placeholder image with PIL if generation fails
3. Return list of image paths
```

**ComfyUI Workflow**:
- Model: SDXL (1280x720, high quality)
- Sampler: Euler
- Steps: 20
- CFG: 7.5
- Denoise: 1.0

**Fallback Placeholder**:
- If GPU unavailable or fails
- PIL creates solid-color image with text
- Allows pipeline to continue

### voice_generator.py (Stage B3)

**Responsibility**: Text-to-speech synthesis

**Algorithm**:
```
1. Check if Coqui TTS is installed
2. If available:
   a. Call: tts --text "..." --model_name tacotron2 --gpu
   b. Write to WAV file
   c. Return path
3. Else fallback to pyttsx3:
   a. Initialize engine
   b. Save to file
   c. Return path
4. Else create silent audio as last resort
```

**Voice Models**:
- Female: tacotron2-DDC (better prosody)
- Male: glow-tts (neutral)

**Fallbacks**:
1. Coqui TTS (primary)
2. pyttsx3 (secondary)
3. Silent WAV (emergency)

### video_assembler.py (Stage C)

**Responsibility**: Combine images + audio into MP4

**Algorithm**:
```
1. Create concat demuxer file:
   file 'scene_0.png'
   duration 6
   file 'scene_1.png'
   duration 6
   ...

2. FFmpeg concat video from images:
   ffmpeg -f concat -i concat.txt \
          -vf scale=1280:720 \
          -c:v libx264 -pix_fmt yuv420p \
          -crf 23 \
          video_no_audio.mp4

3. FFmpeg mux with audio:
   ffmpeg -i video_no_audio.mp4 \
          -i voiceover.wav \
          -c:v copy -c:a aac \
          -map 0:v:0 -map 1:a:0 \
          -shortest \
          final_ad.mp4
```

**Quality Settings**:
- CRF 23: Good balance (lower = better quality)
- H.264: Wide compatibility
- AAC: Good audio quality
- 1280x720 @ 30fps

## Redis Usage

### Data Structures

```
job:{job_id}              HASH
  - status: "running|complete|error"
  - stage: "scrape|script|images|voice|video"
  - message: "Human-readable progress"
  - updated_at: ISO timestamp

queue:ad_jobs             LIST
  - RQ internal job IDs
```

### Caching

```
brand_data:{url}          EXPIRES 24h
  Cached scraped results to avoid re-scraping
```

## Editing Pipeline (Re-render)

When user clicks "Edit & Re-render":

```
1. Parse edits:
   {
     "scenes": [{"scene_id": 0, "text": "new text"}, ...],
     "voiceover_text": "new narration",
     "background_music": "upbeat"
   }

2. Update campaign.script_data with edits

3. **Skip Stage A** (scraping) - reuse brand_data

4. **Skip Stage B1** (script gen) - use existing script but...
   - Update scene text if provided
   - Update narration if provided

5. **Re-run Stage B2** (images) - but only if scene descriptions changed
   - Can optimize by caching images

6. **Re-run Stage B3** (voice) - with new narration text

7. **Re-run Stage C** (video) - combine new audio with images/music

8. Return new video URL
```

**Time Savings**:
- First run: 5-10 minutes (depends on GPU)
- Re-render: 1-2 minutes (skips scraping/script gen)

## API Authentication (Future Enhancement)

Currently: No authentication (demo mode)

```python
# Could add JWT:
from fastapi_jwt_auth import AuthJWT

@app.post("/api/generate-ad")
async def generate_ad(input_data: URLInput, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()
    # Create campaign with user_id
```

## Scaling Strategies

### Horizontal Scaling (Multi-worker)
```bash
# Scale workers for parallel job processing
docker-compose up -d --scale worker=5

# Redis automatically distributes jobs
# Each worker processes one job at a time
```

### Vertical Scaling (More GPU)
```bash
# Use larger Oracle Cloud instances
VM.GPU.A10.2 (2x A10, 48GB VRAM)
# Can generate 2 images in parallel
```

### Caching
```python
# Cache expensive operations:
- Scraped URL data (24h)
- Generated images (indefinitely)
- LLM responses (consider caching similar inputs)
```

## Error Handling

### Retry Strategy
```python
# RQ supports automatic retries:
job = q.enqueue(generate_ad, ..., retry=Retry(max=3, interval=[10, 30, 60]))

# Exponential backoff: 10s, 30s, 60s
```

### Graceful Degradation
- Image generation fails → Use placeholder
- Voiceover fails → Use silent audio
- Video assembly fails → Return error to user

### Logging
- All stages logged to PostgreSQL + Redis
- Frontend can show error details
- Operator can debug via logs

## Performance Metrics

### Typical Times (Oracle Cloud VM.GPU.A10.1)

| Stage | Time | GPU? |
|-------|------|------|
| Stage A (Scrape) | 5-10s | No |
| Stage B1 (Script) | 60-90s | CPUs |
| Stage B2 (Images) | 60-120s each (5×) | Yes |
| Stage B3 (Voice) | 30-60s | No |
| Stage C (Video) | 3-5 min | No |
| **Total (first) ** | **8-10 min** | Mixed |
| **Total (re-render)** | **1-2 min** | Partial |

### Bottlenecks
1. Image generation (GPU-bound when using GPU, CPU-bound otherwise)
2. FFmpeg encoding (CPU-bound)
3. Ollama inference (CPU-bound if no GPU)

### Optimization Tips
1. Pre-warm Ollama with multiple workers
2. Cache Stable Diffusion model in GPU memory
3. Parallelize image generation (requires multiple GPUs)
4. Use faster encoding settings for lower quality (CRF 28+)

## Security Considerations

### Input Validation
```python
# URL validation
if not url.startswith(('http://', 'https://')):
    raise ValueError("Invalid URL")

# Rate limiting (add to FastAPI):
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
@app.post("/api/generate-ad", dependencies=[Depends(limiter.limit("10/minute"))])
```

### Data Privacy
- Database credentials in environment variables
- No API keys in code
- HTTPS in production
- User data isolated by user_id

### Resource Limits
```python
# Prevent abuse:
- Max URL length: 2000 chars
- Max text edits: 500 chars per field
- Max concurrent jobs per user: 5
- Max job duration: 1 hour (timeout)
```

---

Questions? See README.md or QUICKSTART.md for practical usage!
