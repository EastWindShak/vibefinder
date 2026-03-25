"""
FastAPI dependencies for authentication and database access.
"""
import uuid
from typing import Optional
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.security import decode_token, TokenData
from app.services.user_service import UserService


# Security scheme
security = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """
    Represents the current authenticated entity.
    
    Can be either a registered user or a guest session.
    """
    user_id: Optional[uuid.UUID] = None
    session_id: Optional[str] = None
    is_guest: bool = True
    
    @property
    def is_authenticated(self) -> bool:
        """Check if this is a registered user."""
        return self.user_id is not None and not self.is_guest


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[CurrentUser]:
    """
    Get the current user if authenticated, None otherwise.
    
    This dependency does not raise an error if no token is provided,
    allowing endpoints to work for both authenticated and anonymous users.
    """
    if not credentials:
        return None
    
    token_data = decode_token(credentials.credentials)
    if not token_data:
        return None
    
    if token_data.is_guest:
        return CurrentUser(
            session_id=token_data.session_id,
            is_guest=True
        )
    
    if token_data.user_id:
        # Verify user exists
        user_service = UserService(db)
        user = await user_service.get_user_by_id(uuid.UUID(token_data.user_id))
        
        if user and user.is_active:
            return CurrentUser(
                user_id=user.id,
                is_guest=False
            )
    
    return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    """
    Get the current user (required).
    
    This dependency requires authentication and will raise an error
    if no valid token is provided.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token_data = decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if token_data.is_guest:
        return CurrentUser(
            session_id=token_data.session_id,
            is_guest=True
        )
    
    if token_data.user_id:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(uuid.UUID(token_data.user_id))
        
        if user and user.is_active:
            return CurrentUser(
                user_id=user.id,
                is_guest=False
            )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User not found or inactive",
        headers={"WWW-Authenticate": "Bearer"}
    )


async def get_registered_user(
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """
    Get the current registered user (not guest).
    
    This dependency requires a registered user and will raise an error
    for guest sessions.
    """
    if current_user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires a registered user account"
        )
    
    return current_user


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Get a UserService instance."""
    return UserService(db)
