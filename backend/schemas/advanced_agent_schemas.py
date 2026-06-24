from pydantic import BaseModel
from typing import List, Dict, Any

# 1. Brand DNA Memory Agent
class BrandDNAOutput(BaseModel):
    brand_name: str
    brand_voice: str
    brand_personality: str
    target_audience: str
    visual_style: str
    color_palette: List[str]
    emotional_positioning: str
    communication_style: str
    logo_usage_guidelines: List[str]
    photography_style: str
    brand_values: List[str]
    unique_selling_points: List[str]

# 2. Emotional Arc Planner
class EmotionScene(BaseModel):
    scene: int
    emotion: str
    reason: str

class EmotionalArcOutput(BaseModel):
    emotional_arc: List[EmotionScene]

# 3. Creative Brief Generator
class CreativeBriefOutput(BaseModel):
    objective: str
    target_audience: str
    offer: str
    key_message: str
    emotional_goal: str
    visual_direction: str
    marketing_angle: str
    cta: str

# 4. Visual Continuity Engine
class ContinuityRules(BaseModel):
    location: str
    lighting: str
    weather: str
    camera_style: str
    wardrobe: str
    color_palette: List[str]
    time_of_day: str
    visual_mood: str

class VisualContinuityOutput(BaseModel):
    continuity_rules: ContinuityRules

# 5. Multi-Round Review Agent
class MultiRoundReviewOutput(BaseModel):
    marketing_score: float
    creative_score: float
    brand_score: float
    visual_score: float
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]

# 6. Campaign Knowledge Graph Agent
class KnowledgeNode(BaseModel):
    id: str
    type: str
    properties: Dict[str, Any]

class KnowledgeRelationship(BaseModel):
    source: str
    target: str
    relation_type: str

class CampaignKnowledgeGraphOutput(BaseModel):
    nodes: List[KnowledgeNode]
    relationships: List[KnowledgeRelationship]

# 7. Self-Improvement Loop Agent
class SelfImprovementOutput(BaseModel):
    success_patterns: List[str]
    failure_patterns: List[str]
    recommendations: List[str]
    future_rules: List[str]

# 8. Marketing Intelligence Layer
class MarketingIntelligenceOutput(BaseModel):
    market_position: str
    competitor_advantages: List[str]
    competitor_weaknesses: List[str]
    customer_desires: List[str]
    customer_fears: List[str]
    opportunities: List[str]
    recommended_angle: str

# 9. Attention Retention Engine
class AttentionRetentionOutput(BaseModel):
    retention_score: float
    hook_score: float
    pacing_score: float
    engagement_score: float
    cta_score: float
    dropoff_risks: List[str]
    recommendations: List[str]

# 10. Real Motion Video Planner
class MotionShot(BaseModel):
    scene: int
    camera_movement: str
    speed: str
    focus_target: str
    transition: str
    purpose: str

class RealMotionVideoPlannerOutput(BaseModel):
    shots: List[MotionShot]

class QAFix(BaseModel):
    issue: str
    root_cause: str
    fix_strategy: str
    affected_component: str
    priority: str

class AutonomousQAOutput(BaseModel):
    overall_score: float
    issues: List[str]
    root_causes: List[str]
    fixes: List[QAFix]
    components_to_regenerate: List[str]
    expected_score_after_fix: float
    approved: bool
