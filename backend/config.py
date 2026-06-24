import os
import logging
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

import threading

logger = logging.getLogger(__name__)

# Global lock to serialize local Ollama LLM requests across all threads/agents
global_ollama_lock = threading.RLock()

class Settings(BaseSettings):
    model_config = ConfigDict(extra="ignore", env_file=".env")

    # Database
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), 'creoAd.db'))}")
    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "20"))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "40"))
    db_pool_timeout: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    db_pool_recycle: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # MinIO
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "creoad")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "creoad123")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "creoad-videos")
    minio_secure: bool = False

    # Security
    jwt_secret: str = os.getenv("JWT_SECRET", "creoad-dev-secret")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")

    # Service ports (documented + health visibility)
    frontend_port: int = int(os.getenv("FRONTEND_PORT", "3000"))
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    ollama_port: int = int(os.getenv("OLLAMA_PORT", "11434"))
    comfyui_port: int = int(os.getenv("COMFYUI_PORT", "8188"))
    minio_port: int = int(os.getenv("MINIO_PORT", "9000"))
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    
    # Ollama
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "mistral:latest")
    ollama_num_predict: int = int(os.getenv("OLLAMA_NUM_PREDICT", "300"))
    ollama_num_ctx: int = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
    ollama_temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
    ollama_gpu: bool = os.getenv("OLLAMA_GPU", "1").lower() in {"1", "true", "yes", "on"}
    ollama_preferred_models: str = os.getenv(
        "OLLAMA_PREFERRED_MODELS",
        "llama3.2:3b,phi4-mini,phi3:mini,mistral:7b-q4,mistral:latest,mistral:7b,qwen3:8b,qwen2.5:7b",
    )
    ollama_request_timeout: int = int(os.getenv("OLLAMA_REQUEST_TIMEOUT", "900"))
    
    # ComfyUI
    comfyui_url: str = os.getenv("COMFYUI_URL", "http://localhost:8188")
    comfyui_checkpoint: str = os.getenv("COMFYUI_CHECKPOINT", "sdxl_turbo_fp16.safetensors")
    comfyui_width: int = int(os.getenv("COMFYUI_WIDTH", "1024"))
    comfyui_height: int = int(os.getenv("COMFYUI_HEIGHT", "576"))
    comfyui_steps: int = int(os.getenv("COMFYUI_STEPS", "8"))
    comfyui_cfg: float = float(os.getenv("COMFYUI_CFG", "2.5"))
    comfyui_sampler: str = os.getenv("COMFYUI_SAMPLER", "euler_ancestral")

    # Scraping providers
    lightpanda_base_url: str = os.getenv("LIGHTPANDA_BASE_URL", "")
    cloudflare_account_id: str = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    cloudflare_api_token: str = os.getenv("CLOUDFLARE_API_TOKEN", "")
    cloudflare_render_url: str = os.getenv(
        "CLOUDFLARE_RENDER_URL",
        "https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering/content",
    )

    # Local assets
    local_music_dir: str = os.getenv("LOCAL_MUSIC_DIR", "./assets/music")

    # Local generation acceleration
    chatterbox_device: str = os.getenv("CHATTERBOX_DEVICE", "")
    ffmpeg_encoder: str = os.getenv("FFMPEG_ENCODER", "libx264")
    ffmpeg_preset: str = os.getenv("FFMPEG_PRESET", "ultrafast")
    
    # API Keys (if using cloud services)
    claude_api_key: str = os.getenv("CLAUDE_API_KEY", "")
    fal_api_key: str = os.getenv("FAL_API_KEY", "")
    creatomate_api_key: str = os.getenv("CREATOMATE_API_KEY", "")
    
    # Job settings
    job_timeout_scrape: int = 120  # 2 min
    job_timeout_script: int = 180  # 3 min
    job_timeout_images: int = 600  # 10 min
    job_timeout_voice: int = 120   # 2 min
    job_timeout_video: int = 300   # 5 min
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
settings = Settings()

# SEC-C: Log warnings for insecure default credentials on import
if settings.jwt_secret == "creoad-dev-secret":
    logger.warning("SEC: JWT_SECRET is using the default dev value. Set JWT_SECRET env var for production!")
if settings.minio_access_key == "creoad" and settings.minio_secret_key == "creoad123":
    logger.warning("SEC: MinIO is using default credentials (creoad/creoad123). Set MINIO_ACCESS_KEY/MINIO_SECRET_KEY for production!")
