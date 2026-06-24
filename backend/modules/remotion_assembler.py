"""
Phase 4 - Remotion Video Assembler
"""
import subprocess
import json
import os
from typing import Dict, Any

def render_remotion_video(script_data: Dict[str, Any], output_path: str) -> str:
    """
    Calls the frontend Remotion bundle to render the final video.
    Replaces the legacy FFmpeg assembler for highly dynamic, parallelized React components.
    """
    props_path = f"/tmp/remotion_props_{os.urandom(4).hex()}.json"
    with open(props_path, "w") as f:
        json.dump(script_data, f)
        
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
    
    # Example remotion CLI command
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", # entry point
        "MainComposition",
        output_path,
        "--props", props_path
    ]
    
    try:
        subprocess.run(cmd, cwd=frontend_dir, check=True, capture_output=True)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Remotion Render Error: {e.stderr.decode('utf-8')}")
        raise RuntimeError("Failed to render video with Remotion.")
