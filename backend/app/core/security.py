from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
import bcrypt
from cryptography.fernet import Fernet
from pydantic import BaseModel

from app.core.config import settings


class TokenData(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    is_guest: bool = False


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Hash a password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        session_id: str = payload.get("session_id")
        is_guest: bool = payload.get("is_guest", False)
        
        if user_id is None and session_id is None:
            return None
            
        return TokenData(
            user_id=user_id,
            session_id=session_id,
            is_guest=is_guest
        )
    except JWTError:
        return None


# OAuth token encryption
def get_fernet() -> Fernet:
    """Get Fernet instance for OAuth token encryption."""
    return Fernet(settings.OAUTH_ENCRYPTION_KEY.encode())


def encrypt_oauth_token(token: str) -> str:
    """Encrypt an OAuth token for storage."""
    f = get_fernet()
    return f.encrypt(token.encode()).decode()


def decrypt_oauth_token(encrypted_token: str) -> str:
    """Decrypt an OAuth token from storage."""
    f = get_fernet()
    return f.decrypt(encrypted_token.encode()).decode()


def create_guest_session_token(session_id: str) -> str:
    """Create a token for guest users with session-based access."""
    return create_access_token(
        data={"session_id": session_id, "is_guest": True},
        expires_delta=timedelta(hours=24)  # Guest sessions last 24 hours
    )
