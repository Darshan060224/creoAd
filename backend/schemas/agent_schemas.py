from pydantic import BaseModel
from typing import List, Dict

# --- Day 1: Brand Agent ---
class BrandOutput(BaseModel):
    business_type: str
    target_audience: str
    unique_selling_points: List[str]
    tone: str
    brand_personality: str
    customer_pain_points: List[str]
    desired_outcomes: List[str]

# --- Day 2: Marketing Strategist ---
class MarketingOutput(BaseModel):
    hook: str
    problem: str
    agitation: str
    solution: str
    social_proof: str
    cta: str

# --- Day 3: Campaign Generator ---
class CampaignOutput(BaseModel):
    campaign_name: str
    audience: str
    angle: str
    emotional_trigger: str
    objective: str

class CampaignsListOutput(BaseModel):
    campaigns: List[CampaignOutput]

# --- Day 4: Audience Agent ---
class AudienceSegment(BaseModel):
    audience_name: str
    persona_description: str
    pain_points: List[str]
    desires: List[str]
    objections: List[str]

class AudienceOutput(BaseModel):
    audiences: List[AudienceSegment]

# --- Day 5: Creative Director ---
class CreativeDirectorOutput(BaseModel):
    theme: str
    mood: str
    color_palette: List[str]
    camera_style: str
    editing_style: str
    music_style: str

# --- Day 6: Storyboard Agent ---
class StoryboardScene(BaseModel):
    scene_number: int
    duration: int
    hook: str = ""
    problem: str = ""
    solution: str = ""
    proof: str = ""
    cta: str = ""
    description: str

class StoryboardOutput(BaseModel):
    scenes: List[StoryboardScene]

# --- Day 7: Shot Planner ---
class ShotPlan(BaseModel):
    shot_count: int
    shot_duration: float
    camera_type: str
    camera_motion: str
    composition: str

class ShotPlannerOutput(BaseModel):
    # Map of scene name/id to shots list, e.g. {"scene_1": {"shots": [...]}}
    scenes: Dict[str, Dict[str, List[ShotPlan]]]

# --- Day 8: Character Agent ---
class CharacterOutput(BaseModel):
    character_id: str
    gender: str
    age: str
    appearance: str
    clothing: str
    personality: str

# --- Day 9: Prompt Engineer ---
class PromptEngineerOutput(BaseModel):
    prompt: str

# --- Day 10: Quality Reviewer ---
class QualityReviewerOutput(BaseModel):
    face_quality: float
    composition: float
    branding: float
    realism: float
    advertising_quality: float

# --- Day 12: CTO Ad Review ---
class CTOAgentOutput(BaseModel):
    overall_score: float
    marketing_score: float
    creative_score: float
    visual_score: float
    conversion_score: float
    retention_score: float
    issues: List[str]
    root_causes: List[str]
    fixes: List[str]
    components_regenerated: List[str]
    approved: bool
