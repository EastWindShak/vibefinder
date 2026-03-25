"""
Authentication routes for user registration, login, and session management.
"""
import uuid as uuid_module
from typing import Optional
from pydantic import BaseModel, EmailStr

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.user_service import UserService
from app.api.deps import get_current_user, get_registered_user, CurrentUser


router = APIRouter()


# Request/Response Models

class UserRegisterRequest(BaseModel):
    """Request model for user registration."""
    email: EmailStr
    password: str
    display_name: str


class UserLoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Response model for user data."""
    id: str
    email: str
    display_name: str
    is_active: bool
    
    class Config:
        from_attributes = True


class GuestSessionResponse(BaseModel):
    """Response model for guest session creation."""
    access_token: str
    token_type: str = "bearer"
    session_id: str
    message: str = "Guest session created. This session expires in 24 hours."


# Routes

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    
    Creates a new user and returns authentication tokens.
    """
    user_service = UserService(db)
    
    # Check if email already exists
    existing_user = await user_service.get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    # Create user
    user = await user_service.create_user(
        email=request.email,
        password=request.password,
        display_name=request.display_name
    )
    
    # Generate tokens
    tokens = user_service.create_tokens_for_user(user)
    
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password.
    
    Returns authentication tokens for the user.
    """
    user_service = UserService(db)
    
    user = await user_service.authenticate_user(
        email=request.email,
        password=request.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    tokens = user_service.create_tokens_for_user(user)
    
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token
    )


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh an access token using a refresh token.
    
    This endpoint allows users to get a new access token without
    re-authenticating with their credentials.
    """
    from jose import jwt, JWTError
    from app.core.config import settings
    
    # Decode and validate the refresh token - check type field
    try:
        payload = jwt.decode(
            request.refresh_token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Verify it's a refresh token (not an access token)
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type - expected refresh token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token - missing user ID"
            )
            
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired refresh token: {str(e)}"
        )
    
    # Get the user to ensure they still exist and are active
    user_service = UserService(db)
    try:
        user_uuid = uuid_module.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format in token"
        )
    user = await user_service.get_user_by_id(user_uuid)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    # Create new tokens
    tokens = user_service.create_tokens_for_user(user)
    
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token
    )


@router.post("/guest", response_model=GuestSessionResponse)
async def create_guest_session(db: AsyncSession = Depends(get_db)):
    """
    Create a guest session.
    
    Returns a temporary access token for guest users.
    Guest sessions expire after 24 hours and have limited functionality.
    """
    user_service = UserService(db)
    token = user_service.create_guest_session()
    
    # Extract session_id from token (it's in the payload)
    from app.core.security import decode_token
    token_data = decode_token(token.access_token)
    
    return GuestSessionResponse(
        access_token=token.access_token,
        session_id=token_data.session_id if token_data else ""
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser = Depends(get_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current authenticated user's information.
    
    Requires a registered user account (not guest).
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_id(current_user.user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active
    )


@router.get("/status")
async def get_auth_status(
    current_user: Optional[CurrentUser] = Depends(get_current_user)
):
    """
    Get the current authentication status.
    
    Returns whether the user is authenticated and their user type.
    """
    if current_user is None:
        return {
            "authenticated": False,
            "user_type": None
        }
    
    return {
        "authenticated": True,
        "user_type": "guest" if current_user.is_guest else "registered",
        "user_id": str(current_user.user_id) if current_user.user_id else None,
        "session_id": current_user.session_id
    }
