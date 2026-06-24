import threading
import json
import gc

def patch_jobs():
    with open("backend/jobs.py", "r") as f:
        content = f.read()

    # Add missing global variables
    globals_to_add = """
_RETRY_LOCK = __import__('threading').Lock()
_GLOBAL_RETRY_COUNTS = {}

def _redis_get(key: str) -> str | None:
    try:
        return redis_conn.get(key)
    except Exception:
        return None

def _redis_setex(key: str, time: int, value: str) -> None:
    try:
        redis_conn.setex(key, time, value)
    except Exception:
        pass

def _cleanup_gpu_memory() -> None:
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass

def _generate_fallback_voiceover(out_path: str) -> str:
    import subprocess
    subprocess.run(["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "30", out_path, "-y"], check=False)
    return out_path

def _generate_voiceover_with_fallback(text: str, out_path: str, job_id: str = "") -> str:
    try:
        from .modules.voice_generator import generate_voiceover
        return generate_voiceover(text, out_path)
    except Exception as e:
        print(f"Voice generation failed: {e}")
        return _generate_fallback_voiceover(out_path)

def _generate_fallback_music(out_path: str) -> str:
    import subprocess
    subprocess.run(["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "30", out_path, "-y"], check=False)
    return out_path

def _generate_background_music_with_fallback(duration: int, out_path: str, job_id: str = "") -> str:
    try:
        from .modules.music_generator import generate_background_music
        return generate_background_music(duration, out_path)
    except Exception as e:
        print(f"Music generation failed: {e}")
        return _generate_fallback_music(out_path)

def _apply_scene_text_edits(scenes: list, edits: dict) -> list:
    if not edits: return scenes
    # Placeholder for actual edit logic
    return scenes

"""
    if "_RETRY_LOCK" not in content:
        content = content.replace("def _publish_progress", globals_to_add + "def _publish_progress")

    # Re-inject _cleanup_gpu_memory after generations
    if "_cleanup_gpu_memory()" not in content:
        content = content.replace("        # 12. Video Director - AI Camera Motion", "        _cleanup_gpu_memory()\n\n        # 12. Video Director - AI Camera Motion")
        content = content.replace("        # 14. Editor Agent & Assembler", "        _cleanup_gpu_memory()\n\n        # 14. Editor Agent & Assembler")
        
    with open("backend/jobs.py", "w") as f:
        f.write(content)

if __name__ == "__main__":
    patch_jobs()
