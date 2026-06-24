"""
Phase 5 - Production GPU Scheduler
"""
import threading
import time

class GPUScheduler:
    """
    Strict VRAM lock manager.
    Prevents ComfyUI (SDXL) and Ollama (32b models) from running simultaneously and causing OOM.
    """
    def __init__(self):
        self._lock = threading.Lock()
        
    def acquire_vram(self, service_name: str, timeout: int = 300) -> bool:
        print(f"[{service_name}] Requesting VRAM lock...")
        success = self._lock.acquire(timeout=timeout)
        if success:
            print(f"[{service_name}] VRAM lock acquired.")
        else:
            print(f"[{service_name}] Failed to acquire VRAM lock (Timeout).")
        return success
        
    def release_vram(self, service_name: str):
        try:
            self._lock.release()
            print(f"[{service_name}] VRAM lock released.")
        except RuntimeError:
            pass # Already unlocked

gpu_manager = GPUScheduler()
