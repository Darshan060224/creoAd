from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class URLInput(BaseModel):
    url: str
    user_id: Optional[str] = None
    voice_backend: Optional[str] = "chatterbox"
    voice_model: Optional[str] = None

class GenerateJobResponse(BaseModel):
    job_id: str
    campaign_id: str
    status: str
    message: str

class BrandInfo(BaseModel):
    business: Optional[str] = None
    audience: Optional[str] = None
    tone: Optional[str] = None
    usp: Optional[str] = None

class CampaignResponse(BaseModel):
    campaign_id: str
    status: str
    business_url: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    video_url: Optional[str] = None
    video_duration: Optional[int] = None
    brand_data: Optional[BrandInfo] = None
    # We can add more nested fields here to return to the frontend when ready

class EditRequest(BaseModel):
    scenes: Optional[List[Dict[str, Any]]]
    voiceover_text: Optional[str]
    background_music: Optional[str]
    music_volume: Optional[float] = 0.3
    voice_backend: Optional[str] = "chatterbox"
    voice_model: Optional[str] = None

class UserCreate(BaseModel):
    full_name: Optional[str] = None
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None

class TeamMemberInvite(BaseModel):
    email: str
    role: Optional[str] = "Editor"
    name: Optional[str] = None

class TeamMemberOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    status: str
    joined: Optional[str] = None
