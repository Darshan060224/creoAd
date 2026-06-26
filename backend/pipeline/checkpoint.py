"""
Checkpoint system — saves stage outputs to disk so failed
pipelines can resume from the last successful stage instead
of starting over from Stage 1.

Each successful stage call save_checkpoint(), and on pipeline
start each stage checks is_stage_done() to skip already-completed
work. On full success, clear_checkpoint() removes the file.
"""
import json
import os

CHECKPOINT_FILE = "checkpoint.json"


def save_checkpoint(output_dir: str, stage: str, data: dict):
    """Call this after EVERY successful stage completes."""
    path = os.path.join(output_dir, CHECKPOINT_FILE)
    checkpoint = _load(output_dir)
    # Serialize data to JSON-safe form
    safe_data = _make_serializable(data)
    checkpoint[stage] = {
        "completed": True,
        "data": safe_data,
    }
    with open(path, "w") as f:
        json.dump(checkpoint, f, indent=2)


def load_checkpoint(output_dir: str) -> dict:
    """Returns dict of {stage_name: {completed, data}}."""
    return _load(output_dir)


def is_stage_done(output_dir: str, stage: str) -> bool:
    cp = _load(output_dir)
    return cp.get(stage, {}).get("completed", False)


def get_stage_data(output_dir: str, stage: str) -> dict | None:
    cp = _load(output_dir)
    return cp.get(stage, {}).get("data")


def clear_checkpoint(output_dir: str):
    """Remove the checkpoint file after a fully successful pipeline run."""
    path = os.path.join(output_dir, CHECKPOINT_FILE)
    if os.path.exists(path):
        os.remove(path)


def _load(output_dir: str) -> dict:
    path = os.path.join(output_dir, CHECKPOINT_FILE)
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _make_serializable(obj):
    """Recursively convert non-JSON-serializable values to strings."""
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)
