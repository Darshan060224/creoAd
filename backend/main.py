import os
import logging
import importlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import threading

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import redis
import requests
from redis import Redis
from sqlalchemy import text

try:
    from .models import Base, JobMetric
    from .config import settings
    from .db import SessionLocal, get_engine
    from .routes import ads, jobs as routes_jobs, users, websocket
except ImportError:
    from models import Base, JobMetric
    from config import settings
    from db import SessionLocal, get_engine
    from routes import ads, jobs as routes_jobs, users, websocket

logger = logging.getLogger(__name__)

# Initialize database
engine = get_engine()

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize Redis and RQ
redis_conn = Redis.from_url(settings.redis_url, decode_responses=True)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting CreoAd backend")

    def _warm_ollama() -> None:
        try:
            requests.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": "hi",
                    "stream": False,
                    "options": {"num_predict": 1},
                },
                timeout=30,
            )
        except Exception:
            pass

    threading.Thread(target=_warm_ollama, daemon=True).start()
    yield
    # Shutdown
    print("🛑 Shutting down CreoAd backend")

# Create app
app = FastAPI(
    title="CreoAd API",
    description="AI-powered ad generation platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware — SEC-B: Configurable via CORS_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(ads.router, prefix="/api/ads", tags=["ads"])
app.include_router(routes_jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(websocket.router, tags=["websocket"])

# Mount static outputs
os.makedirs("output", exist_ok=True)
app.mount("/output", StaticFiles(directory="output"), name="output")


# ============ HEALTH CHECK ============
@app.get("/health")
async def health_check():
    """Check if all services are running. Returns online/offline status for all services."""
    
    # Check Redis
    try:
        redis_conn.ping()
        redis_status = "online"
    except Exception:
        redis_status = "offline"
    
    # Check PostgreSQL/Database
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        postgres_status = "online"
    except Exception:
        postgres_status = "offline"

    # Check Ollama
    try:
        response = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        ollama_status = "online" if response.ok else "offline"
    except Exception:
        ollama_status = "offline"

    # Check ComfyUI
    try:
        response = requests.get(f"{settings.comfyui_url}/system_stats", timeout=5)
        comfyui_status = "online" if response.ok else "offline"
    except Exception:
        comfyui_status = "offline"

    # Check MinIO
    try:
        minio_module = importlib.import_module("minio")
        Minio = getattr(minio_module, "Minio")
        minio_client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        minio_client.bucket_exists(settings.minio_bucket)
        minio_status = "online"
    except Exception:
        minio_status = "offline"
    
    # FastAPI is always online if this endpoint is responding
    fastapi_status = "online"
    
    return {
        "ollama": ollama_status,
        "comfyui": comfyui_status,
        "redis": redis_status,
        "postgres": postgres_status,
        "minio": minio_status,
        "fastapi": fastapi_status,
        "config": {
            "ollama_model": settings.ollama_model,
            "comfyui_checkpoint": settings.comfyui_checkpoint,
        }
    }


# ============ JOB METRICS ============
@app.get("/api/job-metrics/average")
async def get_average_job_metrics():
    """Get the average duration of pipeline stages across all successful jobs"""
    try:
        db = SessionLocal()
        from sqlalchemy import func
        avg_metrics = db.query(
            func.avg(JobMetric.scrape_time).label('avg_scrape'),
            func.avg(JobMetric.script_time).label('avg_script'),
            func.avg(JobMetric.image_time).label('avg_image'),
            func.avg(JobMetric.voice_time).label('avg_voice'),
            func.avg(JobMetric.music_time).label('avg_music'),
            func.avg(JobMetric.render_time).label('avg_render'),
            func.avg(JobMetric.total_time).label('avg_total')
        ).filter(JobMetric.total_time > 0).first()
        
        db.close()
        
        if not avg_metrics or avg_metrics.avg_total is None:
            return {
                "scrape": 5, "script": 10, "images": 50,
                "voice": 20, "music": 5, "render": 10,
                "total": 150 # default 2 min 30s
            }
            
        return {
            "scrape": round(avg_metrics.avg_scrape or 5, 2),
            "script": round(avg_metrics.avg_script or 10, 2),
            "images": round(avg_metrics.avg_image or 50, 2),
            "voice": round(avg_metrics.avg_voice or 20, 2),
            "music": round(avg_metrics.avg_music or 5, 2),
            "render": round(avg_metrics.avg_render or 10, 2),
            "total": round(avg_metrics.avg_total or 150, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ ROOT ============
@app.get("/")
async def root():
    return {
        "service": "CreoAd - AI Ad Generation Platform",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "generate_ad": "POST /api/ads/generate",
            "job_status": "GET /api/jobs/{job_id}",
            "campaign": "GET /api/ads/{campaign_id}",
            "edit_render": "POST /api/ads/{campaign_id}/edit-and-render",
            "list_campaigns": "GET /api/ads/",
            "register": "POST /api/users/register",
            "login": "POST /api/users/login",
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
