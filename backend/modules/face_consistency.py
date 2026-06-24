"""
Face Consistency Engine (IPAdapter / FaceID)
"""
from typing import Dict, Any

def inject_face_consistency(workflow: Dict[str, Any], face_image_path: str, model_type: str = "IPAdapter") -> Dict[str, Any]:
    """
    Injects FaceID/IPAdapter nodes into a ComfyUI workflow JSON.
    This ensures that characters generated maintain consistent faces across scenes.
    """
    # 1. Add LoadImage node for the reference face
    workflow["900"] = {
        "class_type": "LoadImage",
        "inputs": {"image": face_image_path}
    }
    
    # 2. Add IPAdapterApply node (or FaceID equivalent)
    # The actual node ID might vary depending on custom nodes installed in ComfyUI.
    workflow["901"] = {
        "class_type": "IPAdapterApply",
        "inputs": {
            "ipadapter": ["902", 0], # IPAdapter Loader
            "image": ["900", 0],     # LoadImage
            "model": ["4", 0],       # Load Checkpoint Model
            "weight": 0.85,
            "noise": 0.33
        }
    }
    
    # 3. Add IPAdapterModelLoader
    workflow["902"] = {
        "class_type": "IPAdapterModelLoader",
        "inputs": {"ipadapter_file": "ip-adapter-plus-face_sdxl_vit-h.bin"}
    }
    
    # Reroute the model output from IPAdapter to the KSampler instead of directly from Checkpoint
    # Find the KSampler node dynamically (default ID is "5" in our standard workflow)
    ksampler_id = None
    for node_id, node_data in workflow.items():
        if isinstance(node_data, dict) and node_data.get("class_type") == "KSampler":
            ksampler_id = node_id
            break

    if ksampler_id:
        workflow[ksampler_id]["inputs"]["model"] = ["901", 0]

    return workflow
