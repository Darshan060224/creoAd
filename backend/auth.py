import os
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import bcrypt
import uuid
from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError, ExpiredSignatureError

try:
    from .models import User
    from .db import SessionLocal
    from .config import settings
except ImportError:
    from models import User
    from db import SessionLocal
    from config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")
JWT_SECRET = settings.jwt_secret
JWT_ALGORITHM = "HS256"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(user: User) -> str:
    # H1 FIX: Add expiration to JWT tokens (24 hours)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "iat": now.timestamp(),
        "exp": (now + timedelta(hours=24)).timestamp(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing subject")
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            # C5 FIX: Do NOT auto-create phantom users. If user doesn't exist, reject.
            if not user:
                raise HTTPException(status_code=401, detail="User not found. Please register first.")
            return user
        finally:
            db.close()
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired. Please login again.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
