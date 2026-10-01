from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import verify_token
from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username: str = payload.get("sub", "")
    if username not in [settings.admin_username, "kimbel", "asst"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    
    role = "assistant" if username == "asst" else "attorney"
    attorney_name = "Kimbel B." if settings.demo_mode else "Kimbel Brandon, Esq."
    return {
        "username": username,
        "role": role,
        "name": attorney_name if role == "attorney" else "Practice Assistant (asst)",
    }

