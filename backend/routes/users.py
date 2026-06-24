"""
User auth + team endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

import uuid
from datetime import datetime, timezone

try:
    from ..models import User, TeamMember
    from ..schemas import UserCreate, UserLogin, AuthResponse, UserOut, TeamMemberInvite, TeamMemberOut
    from ..db import SessionLocal
    from ..auth import hash_password, verify_password, create_access_token, get_current_user
except ImportError:
    from models import User, TeamMember
    from schemas import UserCreate, UserLogin, AuthResponse, UserOut, TeamMemberInvite, TeamMemberOut
    from db import SessionLocal
    from auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()





@router.post("/register", response_model=AuthResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    
    # Check if user exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    
    # Create user
    user = User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hash_password(user_data.password),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_access_token(user)
    
    return AuthResponse(
        access_token=token,
        user={"id": user.id, "email": user.email, "full_name": user.full_name}
    )


@router.post("/login", response_model=AuthResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(user)
    
    return AuthResponse(
        access_token=token,
        user={"id": user.id, "email": user.email, "full_name": user.full_name}
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user from token"""
    return UserOut(id=current_user.id, email=current_user.email, full_name=current_user.full_name)


@router.get("/team", response_model=List[TeamMemberOut])
async def get_team_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all team members"""
    members = db.query(TeamMember).filter(TeamMember.user_id == current_user.id).all()
    return members



@router.post("/team/invite", response_model=TeamMemberOut)
async def invite_team_member(
    invite: TeamMemberInvite,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Invite a new team member"""
    existing = db.query(TeamMember).filter(
        TeamMember.email == invite.email.lower(),
        TeamMember.user_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="User already exists in the team")
    
    name = invite.name or invite.email.split('@')[0].capitalize()
    member = TeamMember(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=name,
        email=invite.email.lower(),
        role=invite.role,
        status="Invited",
        joined=datetime.now().strftime("%Y-%m-%d")
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member

