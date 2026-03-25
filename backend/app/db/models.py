import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, 
    Text, JSON, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class User(Base):
    """
    Registered user model.
    Stores user credentials and profile information.
    """
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        nullable=False, 
        index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    oauth_tokens: Mapped[List["OAuthToken"]] = relationship(
        "OAuthToken", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    ia_history: Mapped[List["IAHistory"]] = relationship(
        "IAHistory", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class OAuthToken(Base):
    """
    OAuth2 tokens for YouTube Music integration.
    
    For registered users: linked via user_id, tokens are persistent.
    For guests: linked via session_id, tokens are short-lived.
    """
    __tablename__ = "oauth_tokens"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    # Nullable for guest users
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    # Used for guest session identification
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True, 
        index=True
    )
    # Provider identifier (e.g., "youtube_music")
    provider: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default="youtube_music"
    )
    # Encrypted tokens
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Token expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationship
    user: Mapped[Optional["User"]] = relationship("User", back_populates="oauth_tokens")
    
    # Indexes for efficient lookups
    __table_args__ = (
        Index("idx_oauth_user_provider", "user_id", "provider"),
        Index("idx_oauth_session_provider", "session_id", "provider"),
    )
    
    def __repr__(self) -> str:
        return f"<OAuthToken(id={self.id}, provider={self.provider})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class IAHistory(Base):
    """
    History of AI-generated recommendations.
    
    Stores all recommendation queries and results for:
    - Analytics and improvement
    - "Load 10 more" functionality (avoiding repetitions)
    - User preference learning (for registered users)
    """
    __tablename__ = "ia_history"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    # Nullable for guest users
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    # Used for guest session tracking
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True, 
        index=True
    )
    # Type of query: "mood" or "audio"
    query_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Input data (mood text or audio metadata)
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Generated recommendations
    recommendations: Mapped[dict] = mapped_column(JSON, nullable=False)
    # User feedback on recommendations (likes/dislikes)
    feedback: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False,
        index=True
    )
    
    # Relationship
    user: Mapped[Optional["User"]] = relationship("User", back_populates="ia_history")
    
    # Indexes
    __table_args__ = (
        Index("idx_history_user_created", "user_id", "created_at"),
        Index("idx_history_session_created", "session_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<IAHistory(id={self.id}, query_type={self.query_type})>"


class UserPreferenceFeedback(Base):
    """
    Explicit user feedback on songs.
    
    Used to track likes/dislikes for ChromaDB preference updates.
    Only for registered users.
    """
    __tablename__ = "user_preference_feedback"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # Song identification
    song_title: Mapped[str] = mapped_column(String(255), nullable=False)
    song_artist: Mapped[str] = mapped_column(String(255), nullable=False)
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Feedback: 1 for like, -1 for dislike
    feedback_score: Mapped[int] = mapped_column(nullable=False)
    # Additional metadata
    genre: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mood_tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    
    __table_args__ = (
        Index("idx_feedback_user_song", "user_id", "song_title", "song_artist"),
    )
    
    def __repr__(self) -> str:
        return f"<UserPreferenceFeedback(user_id={self.user_id}, song={self.song_title})>"
