from datetime import datetime, timedelta, timezone
from typing import Optional
from app.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Support both PyJWT and python-jose transparently
try:
    import jwt
    from jwt.exceptions import PyJWTError as JWTError
except ImportError:
    try:
        from jose import JWTError, jwt
    except ImportError:
        raise ImportError("Neither 'PyJWT' nor 'python-jose' is installed. Please install PyJWT or python-jose.")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    # PyJWT returns str in v2+, python-jose returns str
    if isinstance(encoded_jwt, bytes):
        encoded_jwt = encoded_jwt.decode("utf-8")
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None
