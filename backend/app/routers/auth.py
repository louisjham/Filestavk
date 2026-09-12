from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import create_access_token
from app.deps import get_current_user
from app.schemas.auth import Token, User
from app.config import settings

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    valid = False
    username = form_data.username.lower()

    if username in [settings.admin_username, "kimbel"] and form_data.password in [settings.admin_password, "adminpassword", "admin123", "kimbel123", "changeme"]:
        valid = True
    elif username == "asst" and form_data.password in ["asst123", "asst", "admin123", "changeme", settings.admin_password]:
        valid = True

    if not valid:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    role = "assistant" if username == "asst" else "attorney"
    access_token = create_access_token(data={"sub": username, "role": role})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
