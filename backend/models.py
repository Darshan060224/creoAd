from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, JSON, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    job_id = Column(String, index=True, nullable=True)
    business_url = Column(String)
    status = Column(String, default="queued")  # queued, analyzing, strategizing, writing, storyboarding, planning, generating, assembling, done, error
    
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    video_url = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    # CODE-D: Cascade deletes so removing a campaign removes all associated data
    brands = relationship("Brand", cascade="all, delete-orphan", passive_deletes=True)
    videos = relationship("Video", cascade="all, delete-orphan", passive_deletes=True)
    shots = relationship("Shot", cascade="all, delete-orphan", passive_deletes=True)
    storyboard_scenes = relationship("StoryboardScene", cascade="all, delete-orphan", passive_deletes=True)
    images = relationship("Image", cascade="all, delete-orphan", passive_deletes=True)
    scores = relationship("Score", cascade="all, delete-orphan", passive_deletes=True)
    job_metrics = relationship("JobMetric", cascade="all, delete-orphan", passive_deletes=True)

class Brand(Base):
    __tablename__ = "brands"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    business = Column(String)
    audience = Column(String)
    tone = Column(String)
    usp = Column(String)

class MarketingStrategy(Base):
    __tablename__ = "marketing_strategies"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    pain_points = Column(JSON) # List of strings
    emotion = Column(String)
    angle = Column(String)

class AdStructure(Base):
    __tablename__ = "ad_structures"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    hook_duration = Column(Float)
    problem_duration = Column(Float)
    solution_duration = Column(Float)
    proof_duration = Column(Float)
    cta_duration = Column(Float)

class StoryboardScene(Base):
    __tablename__ = "storyboard_scenes"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    scene_number = Column(Integer)
    purpose = Column(String)
    duration = Column(Float)
    emotion = Column(String)
    message = Column(Text)

class Shot(Base):
    __tablename__ = "shots"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    scene_id = Column(String, ForeignKey("storyboard_scenes.id"))
    shot_type = Column(String) # 'closeup', 'wide', etc.
    duration = Column(Float)
    camera_movement = Column(String)
    transition = Column(String)
    speed = Column(String)

class Prompt(Base):
    __tablename__ = "prompts"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    shot_id = Column(String, ForeignKey("shots.id"))
    text = Column(Text)
    camera = Column(String)
    lens = Column(String)
    lighting = Column(String)
    composition = Column(String)
    advertising_style = Column(String)

class Image(Base):
    __tablename__ = "images"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    shot_id = Column(String, ForeignKey("shots.id"))
    url = Column(String)
    workflow_used = Column(String)

class Video(Base):
    __tablename__ = "videos"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    url = Column(String)
    type = Column(String) # 'final' or 'scene'

class Voiceover(Base):
    __tablename__ = "voiceovers"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    url = Column(String)
    emotion = Column(String)
    pace = Column(String)
    energy = Column(String)
    emphasis = Column(String)

class Music(Base):
    __tablename__ = "music"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    url = Column(String)

class Review(Base):
    __tablename__ = "reviews"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    target_type = Column(String) # 'image' or 'video'
    target_id = Column(String) # e.g. Image ID or Video ID
    score = Column(Float)
    feedback = Column(Text)

class Score(Base):
    __tablename__ = "scores"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    marketing = Column(Float)
    visual_quality = Column(Float)
    retention = Column(Float)
    branding = Column(Float)
    cta = Column(Float)
    fixes = Column(JSON) # List of recommended fixes
    estimated_ctr = Column(Float, nullable=True)
    hook_rate = Column(Float, nullable=True)
    conversion_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    creative_score = Column(Float, nullable=True)
    issues = Column(JSON, nullable=True) # List of strings
    root_causes = Column(JSON, nullable=True) # List of strings
    components_regenerated = Column(JSON, nullable=True) # List of strings
    approved = Column(Boolean, default=False)

class JobLog(Base):
    __tablename__ = "job_logs"
    
    id = Column(String, primary_key=True)
    campaign_id = Column(String, index=True)
    job_id = Column(String)
    stage = Column(String)
    status = Column(String)
    message = Column(Text)
    duration_ms = Column(Integer)
    created_at = Column(DateTime, default=utcnow)

class TeamMember(Base):
    __tablename__ = "team_members"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    role = Column(String, nullable=False)
    status = Column(String, default="Invited")
    joined = Column(String)

class Character(Base):
    __tablename__ = "characters"
    id = Column(String, primary_key=True)
    character_id = Column(String, unique=True, index=True)
    gender = Column(String)
    age = Column(String)
    hair = Column(String)
    beard = Column(String)
    
class CampaignCharacter(Base):
    __tablename__ = "campaign_characters"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    character_id = Column(String, ForeignKey("characters.character_id"))

class CompetitorAnalysis(Base):
    __tablename__ = "competitor_analysis"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    competitors = Column(JSON) # List of competitors and positioning
    market_gap = Column(String)
    winning_angles = Column(JSON, nullable=True) # List of strings
    winning_hooks = Column(JSON, nullable=True) # List of strings
    winning_styles = Column(JSON, nullable=True) # List of strings

class AudienceSegment(Base):
    __tablename__ = "audience_segments"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    segments = Column(JSON) # List of audience segments

class BrandMemory(Base):
    __tablename__ = "brand_memory"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    brand_name = Column(String)
    json_state = Column(JSON) # Extracted tone, colors, audiences, past successful hooks

class CharacterIdentity(Base):
    __tablename__ = "character_identities"
    id = Column(String, primary_key=True)
    brand_id = Column(String, ForeignKey("brand_memory.id"))
    comfyui_face_embedding = Column(String) # Path to stored embedding/tensor

class MotionPlan(Base):
    __tablename__ = "motion_plans"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    scene_id = Column(String, ForeignKey("storyboard_scenes.id"))
    camera_type = Column(String)
    transition_type = Column(String)
    speed = Column(String)
    energy = Column(String)

class TextAnimation(Base):
    __tablename__ = "text_animations"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    shot_id = Column(String, ForeignKey("shots.id"))
    text = Column(String)
    animation_type = Column(String)
    duration = Column(Float)
    sync = Column(String)

class SoundEvent(Base):
    __tablename__ = "sound_events"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    timeline_data = Column(JSON) # List of {"time": float, "effect": string}

class Persona(Base):
    __tablename__ = "personas"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    persona_name = Column(String)
    pain_points = Column(JSON) # List of strings
    desires = Column(JSON) # List of strings

class RetentionScore(Base):
    __tablename__ = "retention_scores"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    dropoff_risk = Column(Float)
    scene = Column(Integer)
    reason = Column(String)

class VideoJob(Base):
    __tablename__ = "video_jobs"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    video_type = Column(String) # 'wan2.1', 'ltx', etc.
    status = Column(String)
    url = Column(String)
    
class CampaignLearning(Base):
    __tablename__ = "campaign_learnings"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    lessons = Column(JSON) # List of strings

class HookMemory(Base):
    __tablename__ = "hook_memory"
    id = Column(String, primary_key=True)
    industry = Column(String, index=True)
    hook = Column(String)
    score = Column(Float)

class SceneMemory(Base):
    __tablename__ = "scene_memory"
    id = Column(String, primary_key=True)
    scene_type = Column(String)
    camera = Column(String)
    performance = Column(String)

class MotionMemory(Base):
    __tablename__ = "motion_memory"
    id = Column(String, primary_key=True)
    industry = Column(String, index=True)
    motion = Column(String)
    score = Column(Float)

class CTAMemory(Base):
    __tablename__ = "cta_memory"
    id = Column(String, primary_key=True)
    cta = Column(String)
    score = Column(Float)

class JobMetric(Base):
    __tablename__ = "job_metrics"
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    job_id = Column(String, index=True)
    scrape_time = Column(Float, default=0.0)
    script_time = Column(Float, default=0.0)
    image_time = Column(Float, default=0.0)
    voice_time = Column(Float, default=0.0)
    music_time = Column(Float, default=0.0)
    render_time = Column(Float, default=0.0)
    total_time = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utcnow)
