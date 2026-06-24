from pydantic import BaseModel
from typing import List

class CompetitorAnalysis(BaseModel):
    competitor_name: str
    strengths: List[str]
    weaknesses: List[str]
    current_offers: List[str]

class CompetitorAgentOutput(BaseModel):
    competitors: List[CompetitorAnalysis]

class HookItem(BaseModel):
    hook_text: str
    category: str = "Unknown"
    emotion_triggered: str
    estimated_retention: float
    score: float = 0.0

class HookGeneratorOutput(BaseModel):
    hooks: List[HookItem]

class CTAItem(BaseModel):
    cta_text: str
    urgency_level: str
    clarity_score: float

class CTAGeneratorOutput(BaseModel):
    ctas: List[CTAItem]
