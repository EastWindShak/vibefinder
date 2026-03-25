"""
User service for managing registered users and guests.

Handles user authentication, registration, and session management.
"""
import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, OAuthToken, IAHistory, UserPreferenceFeedback
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_guest_session_token,
    encrypt_oauth_token,
    decrypt_oauth_token,
    Token
)


class UserService:
    """Service for user-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_user(
        self,
        email: str,
        password: str,
        display_name: str
    ) -> User:
        """
        Create a new registered user.
        
        Args:
            email: User's email address
            password: Plain text password
            display_name: Display name
            
        Returns:
            Created User object
        """
        user = User(
            email=email.lower(),
            hashed_password=get_password_hash(password),
            display_name=display_name
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email address."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get a user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def authenticate_user(
        self,
        email: str,
        password: str
    ) -> Optional[User]:
        """
        Authenticate a user by email and password.
        
        Args:
            email: User's email
            password: Plain text password
            
        Returns:
            User object if authenticated, None otherwise
        """
        user = await self.get_user_by_email(email)
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        return user
    
    def create_tokens_for_user(self, user: User) -> Token:
        """
        Create access and refresh tokens for a user.
        
        Args:
            user: The authenticated user
            
        Returns:
            Token object with access and refresh tokens
        """
        access_token = create_access_token(
            data={"sub": str(user.id), "is_guest": False}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)}
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token
        )
    
    def create_guest_session(self) -> Token:
        """
        Create a guest session with a temporary token.
        
        Returns:
            Token object with session-based access token
        """
        session_id = str(uuid.uuid4())
        access_token = create_guest_session_token(session_id)
        
        return Token(
            access_token=access_token,
            refresh_token=None  # Guests don't get refresh tokens
        )
    
    # OAuth Token Management
    
    async def store_oauth_token(
        self,
        user_id: Optional[uuid.UUID],
        session_id: Optional[str],
        access_token: str,
        refresh_token: Optional[str],
        expires_at: Optional[datetime],
        provider: str = "youtube_music"
    ) -> OAuthToken:
        """
        Store an OAuth token (encrypted).
        
        Args:
            user_id: User ID (for registered users)
            session_id: Session ID (for guests)
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_at: Token expiration time
            provider: OAuth provider name
            
        Returns:
            Created OAuthToken object
        """
        oauth_token = OAuthToken(
            user_id=user_id,
            session_id=session_id,
            provider=provider,
            access_token=encrypt_oauth_token(access_token),
            refresh_token=encrypt_oauth_token(refresh_token) if refresh_token else None,
            expires_at=expires_at
        )
        
        self.db.add(oauth_token)
        await self.db.commit()
        await self.db.refresh(oauth_token)
        
        return oauth_token
    
    async def get_oauth_token(
        self,
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
        provider: str = "youtube_music"
    ) -> Optional[OAuthToken]:
        """
        Get an OAuth token for a user or session.
        
        Args:
            user_id: User ID (for registered users)
            session_id: Session ID (for guests)
            provider: OAuth provider name
            
        Returns:
            OAuthToken if found, None otherwise
        """
        query = select(OAuthToken).where(OAuthToken.provider == provider)
        
        if user_id:
            query = query.where(OAuthToken.user_id == user_id)
        elif session_id:
            query = query.where(OAuthToken.session_id == session_id)
        else:
            return None
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_decrypted_oauth_token(
        self,
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
        provider: str = "youtube_music"
    ) -> Optional[dict]:
        """
        Get decrypted OAuth tokens.
        
        Returns:
            Dict with 'access_token' and 'refresh_token' keys, or None
        """
        oauth = await self.get_oauth_token(user_id, session_id, provider)
        
        if not oauth:
            return None
        
        return {
            "access_token": decrypt_oauth_token(oauth.access_token),
            "refresh_token": decrypt_oauth_token(oauth.refresh_token) if oauth.refresh_token else None,
            "expires_at": oauth.expires_at,
            "is_expired": oauth.is_expired
        }
    
    async def update_oauth_token(
        self,
        oauth_id: uuid.UUID,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> Optional[OAuthToken]:
        """
        Update an OAuth token (e.g., after refresh).
        
        Args:
            oauth_id: ID of the OAuth token to update
            access_token: New access token
            refresh_token: New refresh token (optional)
            expires_at: New expiration time
            
        Returns:
            Updated OAuthToken or None
        """
        result = await self.db.execute(
            select(OAuthToken).where(OAuthToken.id == oauth_id)
        )
        oauth = result.scalar_one_or_none()
        
        if not oauth:
            return None
        
        oauth.access_token = encrypt_oauth_token(access_token)
        if refresh_token:
            oauth.refresh_token = encrypt_oauth_token(refresh_token)
        if expires_at:
            oauth.expires_at = expires_at
        
        await self.db.commit()
        await self.db.refresh(oauth)
        
        return oauth
    
    async def delete_oauth_token(
        self,
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
        provider: str = "youtube_music"
    ) -> bool:
        """Delete OAuth tokens for a user or session."""
        oauth = await self.get_oauth_token(user_id, session_id, provider)
        
        if not oauth:
            return False
        
        await self.db.delete(oauth)
        await self.db.commit()
        
        return True
    
    # History Management
    
    async def save_recommendation_history(
        self,
        user_id: Optional[uuid.UUID],
        session_id: Optional[str],
        query_type: str,
        input_data: dict,
        recommendations: dict
    ) -> IAHistory:
        """
        Save a recommendation query to history.
        
        Args:
            user_id: User ID (for registered users)
            session_id: Session ID (for guests)
            query_type: Type of query ('mood' or 'audio')
            input_data: The input that generated recommendations
            recommendations: The generated recommendations
            
        Returns:
            Created IAHistory object
        """
        history = IAHistory(
            user_id=user_id,
            session_id=session_id,
            query_type=query_type,
            input_data=input_data,
            recommendations=recommendations
        )
        
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        
        return history

    async def get_user_likes(
        self,
        user_id: uuid.UUID,
        limit: int = 100
    ) -> list:
        """
        Get user's liked songs.
        """
        print(user_id)
        query = select(UserPreferenceFeedback).where(UserPreferenceFeedback.user_id == user_id, UserPreferenceFeedback.feedback_score == 1).order_by(UserPreferenceFeedback.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_user_dislikes(
        self,
        user_id: uuid.UUID,
        limit: int = 100
    ) -> list:
        """
        Get user's disliked songs.
        """
        print(user_id)
        query = select(UserPreferenceFeedback).where(UserPreferenceFeedback.user_id == user_id, UserPreferenceFeedback.feedback_score == 0).order_by(UserPreferenceFeedback.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_recommendation_history(
        self,
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> list:
        """
        Get recommendation history for a user or session.
        
        Args:
            user_id: User ID (for registered users)
            session_id: Session ID (for guests)
            limit: Maximum number of records to return
            
        Returns:
            List of IAHistory objects
        """
        query = select(IAHistory).order_by(IAHistory.created_at.desc()).limit(limit)
        
        if user_id:
            query = query.where(IAHistory.user_id == user_id)
        elif session_id:
            query = query.where(IAHistory.session_id == session_id)
        else:
            return []
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_history_item_by_id(
        self,
        history_id: str,
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None
    ) -> Optional[IAHistory]:
        """
        Get a specific history item by ID.
        
        Args:
            history_id: The UUID of the history item
            user_id: User ID (for registered users)
            session_id: Session ID (for guests)
            
        Returns:
            IAHistory object or None if not found
        """
        try:
            history_uuid = uuid.UUID(history_id)
        except ValueError:
            return None
        
        query = select(IAHistory).where(IAHistory.id == history_uuid)
        
        # Ensure the user can only access their own history
        if user_id:
            query = query.where(IAHistory.user_id == user_id)
        elif session_id:
            query = query.where(IAHistory.session_id == session_id)
        else:
            return None
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
