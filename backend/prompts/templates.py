"""
Industry Templates and Prompt Templates Library
"""
INDUSTRY_TEMPLATES = {
    "Restaurant": {
        "visual_style": "Warm, appetizing, shallow depth of field, vibrant colors",
        "camera_style": "Macro food shots, slow tracking, dynamic panning",
        "music_mood": "Upbeat, acoustic, energetic",
        "color_palette": ["#E63946", "#F1FAEE", "#A8DADC", "#457B9D"]
    },
    "Gym": {
        "visual_style": "High contrast, gritty, sweat detail, dramatic lighting",
        "camera_style": "Fast cuts, handheld, low angle heroic shots",
        "music_mood": "Intense, bass-heavy, electronic",
        "color_palette": ["#000000", "#FFFFFF", "#FF0000", "#1C1C1C"]
    },
    "Real Estate": {
        "visual_style": "Bright, airy, natural lighting, clean lines",
        "camera_style": "Smooth drone tracking, wide architectural angles, slow pan",
        "music_mood": "Corporate, uplifting, acoustic",
        "color_palette": ["#F8F9FA", "#E9ECEF", "#DEE2E6", "#CED4DA"]
    },
    "SaaS": {
        "visual_style": "Minimalist, futuristic, dark mode with neon accents",
        "camera_style": "Static isometric, smooth digital push-in",
        "music_mood": "Lo-fi, ambient electronic, futuristic",
        "color_palette": ["#0D1B2A", "#1B263B", "#415A77", "#778DA9"]
    }
}

PROMPT_TEMPLATES = {
    "Cinematic": "Shot on 35mm lens, cinematic lighting, anamorphic lens flare, 8k resolution, professional color grading, film grain, highly detailed.",
    "Documentary": "Handheld camera feel, natural lighting, raw emotion, authentic, documentary style, realistic photography, 4k.",
    "Studio": "Studio lighting, clean backdrop, sharp focus, professional product photography, high key lighting, crisp details, 8k."
}
