import subprocess
import os

output_dir = "/tmp/creoAd_jobs/test_job"
os.makedirs(output_dir, exist_ok=True)
img = os.path.abspath("test.jpg")
subprocess.run(["convert", "-size", "1920x1080", "xc:white", img])

from backend.modules.video_assembler import CAMERA_EFFECTS
fps = 30
w, h = 1920, 1080
shot_dur = 3.0
camera_type = "zoom_in"
vf = CAMERA_EFFECTS.get(camera_type, CAMERA_EFFECTS["static"]).format(d=int(shot_dur * fps))
vf += f":s={w}x{h}:fps={fps}"
vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}," + vf + ",format=yuv420p"

cmd = [
    "ffmpeg", "-y",
    "-loop", "1",
    "-t", str(shot_dur + 0.6),
    "-i", img,
    "-vf", vf,
    "-c:v", "libx264",
    "-t", str(shot_dur + 0.6),
    "-an",
    "/tmp/test_clip.mp4"
]
subprocess.run(cmd, check=True)
print("SUCCESS!")
