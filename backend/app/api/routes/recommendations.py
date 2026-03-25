"""
Recommendation routes for AI-powered music discovery.
"""
from typing import Optional, List
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.deps import get_current_user, get_current_user_optional, CurrentUser
from app.services.recommendation_service import (
    get_recommendation_service,
    RecommendationService,
    RecommendationRequest
)
from app.services.user_service import UserService
from app.db.chromadb_client import get_chromadb_client


router = APIRouter()


# Request/Response Models

class MoodRecommendationRequest(BaseModel):
    """Request for mood-based recommendations."""
    mood: str
    previous_songs: Optional[List[str]] = None


class AudioRecommendationRequest(BaseModel):
    """Request for audio-based recommendations (identified song)."""
    song_title: str
    song_artist: str
    song_genre: Optional[str] = None
    previous_songs: Optional[List[str]] = None


class AudioAnalysisRecommendationRequest(BaseModel):
    """Request for recommendations based on audio analysis (unidentified song)."""
    mood_tags: List[str]
    genre_tags: List[str]
    tempo_description: str = "moderate"
    energy_level: str = "medium"
    search_queries: Optional[List[str]] = None  # Pre-generated queries
    previous_songs: Optional[List[str]] = None


class CombinedRecommendationRequest(BaseModel):
    """Request for combined mood + audio recommendations."""
    mood: Optional[str] = None
    song_title: Optional[str] = None
    song_artist: Optional[str] = None
    song_genre: Optional[str] = None
    previous_songs: Optional[List[str]] = None


class SongResponse(BaseModel):
    """Response model for a single song."""
    title: str
    artist: str
    reason: Optional[str] = None
    genre: Optional[str] = None
    mood: Optional[str] = None
    video_id: Optional[str] = None
    album: Optional[str] = None
    duration: Optional[str] = None
    thumbnail_url: Optional[str] = None


class RecommendationsResponse(BaseModel):
    """Response model for recommendations."""
    recommendations: List[SongResponse]
    input_type: str
    session_id: str
    is_continuation: bool = False
    used_chromadb: bool = False
    chromadb_info: Optional[str] = None


class FeedbackRequest(BaseModel):
    """Request for song feedback (like/dislike)."""
    song_title: str
    artist: str
    feedback_score: int  # 1 for like, -1 for dislike
    video_id: Optional[str] = None
    genre: Optional[str] = None
    mood_tags: Optional[List[str]] = None


class PreferenceItem(BaseModel):
    """A single preference item (like or dislike)."""
    id: str
    song_title: str
    artist: str
    genre: Optional[str] = None
    video_id: Optional[str] = None
    mood_tags: Optional[List[str]] = None


class PreferencesResponse(BaseModel):
    """Response with user preferences."""
    preferences: List[PreferenceItem]
    total: int
    type: str  # "likes" or "dislikes"


class PreferencesCountResponse(BaseModel):
    """Response with preference counts."""
    likes: int
    dislikes: int


# Routes

@router.post("/mood", response_model=RecommendationsResponse)
async def get_mood_recommendations(
    request: MoodRecommendationRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get music recommendations based on a mood description.
    
    Works for both registered users and guests.
    - Registered users: recommendations are personalized based on stored preferences
    - Guests: recommendations are based solely on the mood input
    
    Use the `previous_songs` parameter to get "10 more" recommendations
    while avoiding previously suggested songs.
    """
    recommendation_service = get_recommendation_service()
    
    # Get YouTube auth if available
    youtube_auth = None
    if current_user:
        user_service = UserService(db)
        oauth = await user_service.get_decrypted_oauth_token(
            user_id=current_user.user_id,
            session_id=current_user.session_id
        )
        if oauth and not oauth.get("is_expired"):
            youtube_auth = oauth.get("access_token")
    
    # Build request
    rec_request = RecommendationRequest(
        input_type="mood",
        mood_text=request.mood,
        previous_songs=request.previous_songs,
        session_id=current_user.session_id if current_user and current_user.is_guest else None
    )
    
    # Get recommendations
    try:
        response = await recommendation_service.get_recommendations(
            request=rec_request,
            user_id=current_user.user_id if current_user else None,
            youtube_auth_headers=youtube_auth
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )
    
    # Save to history
    if current_user:
        user_service = UserService(db)
        await user_service.save_recommendation_history(
            user_id=current_user.user_id,
            session_id=current_user.session_id,
            query_type="mood",
            input_data={"mood": request.mood},
            recommendations=response.to_dict()
        )
    
    return RecommendationsResponse(
        recommendations=[
            SongResponse(**r.to_dict()) for r in response.recommendations
        ],
        input_type=response.input_type,
        session_id=response.session_id,
        is_continuation=response.is_continuation,
        used_chromadb=response.used_chromadb,
        chromadb_info=response.chromadb_info
    )


@router.post("/audio", response_model=RecommendationsResponse)
async def get_audio_recommendations(
    request: AudioRecommendationRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get music recommendations based on an identified song.
    
    This endpoint is typically called after identifying a song via the /audio/identify endpoint.
    
    Works for both registered users and guests.
    """
    recommendation_service = get_recommendation_service()
    
    # Get YouTube auth if available
    youtube_auth = None
    if current_user:
        user_service = UserService(db)
        oauth = await user_service.get_decrypted_oauth_token(
            user_id=current_user.user_id,
            session_id=current_user.session_id
        )
        if oauth and not oauth.get("is_expired"):
            youtube_auth = oauth.get("access_token")
    
    # Build request
    rec_request = RecommendationRequest(
        input_type="audio",
        song_title=request.song_title,
        song_artist=request.song_artist,
        song_genre=request.song_genre,
        previous_songs=request.previous_songs,
        session_id=current_user.session_id if current_user and current_user.is_guest else None
    )
    
    # Get recommendations
    try:
        response = await recommendation_service.get_recommendations(
            request=rec_request,
            user_id=current_user.user_id if current_user else None,
            youtube_auth_headers=youtube_auth
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )
    
    # Save to history
    if current_user:
        user_service = UserService(db)
        await user_service.save_recommendation_history(
            user_id=current_user.user_id,
            session_id=current_user.session_id,
            query_type="audio",
            input_data={
                "song_title": request.song_title,
                "song_artist": request.song_artist,
                "song_genre": request.song_genre
            },
            recommendations=response.to_dict()
        )
    
    return RecommendationsResponse(
        recommendations=[
            SongResponse(**r.to_dict()) for r in response.recommendations
        ],
        input_type=response.input_type,
        session_id=response.session_id,
        is_continuation=response.is_continuation,
        used_chromadb=response.used_chromadb,
        chromadb_info=response.chromadb_info
    )


@router.post("/audio-analysis", response_model=RecommendationsResponse)
async def get_audio_analysis_recommendations(
    request: AudioAnalysisRecommendationRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get music recommendations based on audio analysis of an unidentified song.
    
    CASE 3: When a song cannot be identified by Shazam, the audio is
    analyzed by CLAP to extract mood, genre, tempo, and energy characteristics.
    
    This endpoint takes those characteristics and finds similar music on YouTube Music.
    
    The analysis results come from the /audio/identify endpoint when identification fails.
    """
    recommendation_service = get_recommendation_service()
    
    # Get YouTube auth if available
    youtube_auth = None
    if current_user:
        user_service = UserService(db)
        oauth = await user_service.get_decrypted_oauth_token(
            user_id=current_user.user_id,
            session_id=current_user.session_id
        )
        if oauth and not oauth.get("is_expired"):
            youtube_auth = oauth.get("access_token")
    
    # Build request with CLAP audio analysis data
    rec_request = RecommendationRequest(
        input_type="audio_analysis",
        audio_mood_tags=request.mood_tags,
        audio_genre_tags=request.genre_tags,
        audio_tempo=request.tempo_description,
        audio_energy=request.energy_level,
        audio_search_queries=request.search_queries,  # Pre-generated by CLAP
        previous_songs=request.previous_songs,
        session_id=current_user.session_id if current_user and current_user.is_guest else None
    )
    
    # Get recommendations
    try:
        response = await recommendation_service.get_recommendations(
            request=rec_request,
            user_id=current_user.user_id if current_user else None,
            youtube_auth_headers=youtube_auth
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )
    
    # Save to history
    if current_user:
        user_service = UserService(db)
        await user_service.save_recommendation_history(
            user_id=current_user.user_id,
            session_id=current_user.session_id,
            query_type="audio_analysis",
            input_data={
                "mood_tags": request.mood_tags,
                "genre_tags": request.genre_tags,
                "tempo": request.tempo_description,
                "energy": request.energy_level
            },
            recommendations=response.to_dict()
        )
    
    return RecommendationsResponse(
        recommendations=[
            SongResponse(**r.to_dict()) for r in response.recommendations
        ],
        input_type="audio_analysis",
        session_id=response.session_id,
        is_continuation=response.is_continuation,
        used_chromadb=response.used_chromadb,
        chromadb_info=response.chromadb_info
    )


@router.post("/combined", response_model=RecommendationsResponse)
async def get_combined_recommendations(
    request: CombinedRecommendationRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get music recommendations based on both mood description AND identified song.
    
    This endpoint combines context from:
    - A mood/text description from the user
    - An identified song (title, artist, genre)
    
    The AI will use both inputs to generate more personalized recommendations.
    At least one of mood or song information must be provided.
    """
    # Validate that at least one input is provided
    has_mood = request.mood and request.mood.strip()
    has_song = request.song_title and request.song_artist
    
    if not has_mood and not has_song:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least mood or song information must be provided"
        )
    
    recommendation_service = get_recommendation_service()
    
    # Get YouTube auth if available
    youtube_auth = None
    if current_user:
        user_service = UserService(db)
        oauth = await user_service.get_decrypted_oauth_token(
            user_id=current_user.user_id,
            session_id=current_user.session_id
        )
        if oauth and not oauth.get("is_expired"):
            youtube_auth = oauth.get("access_token")
    
    # Determine input type based on what was provided
    if has_mood and has_song:
        input_type = "combined"
    elif has_song:
        input_type = "audio"
    else:
        input_type = "mood"
    
    # Build request
    rec_request = RecommendationRequest(
        input_type=input_type,
        mood_text=request.mood if has_mood else None,
        song_title=request.song_title if has_song else None,
        song_artist=request.song_artist if has_song else None,
        song_genre=request.song_genre,
        previous_songs=request.previous_songs,
        session_id=current_user.session_id if current_user and current_user.is_guest else None
    )
    
    # Get recommendations
    try:
        response = await recommendation_service.get_recommendations(
            request=rec_request,
            user_id=current_user.user_id if current_user else None,
            youtube_auth_headers=youtube_auth
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )
    
    # Save to history
    if current_user:
        user_service = UserService(db)
        input_data = {}
        if has_mood:
            input_data["mood"] = request.mood
        if has_song:
            input_data["song_title"] = request.song_title
            input_data["song_artist"] = request.song_artist
            input_data["song_genre"] = request.song_genre
        
        await user_service.save_recommendation_history(
            user_id=current_user.user_id,
            session_id=current_user.session_id,
            query_type=input_type,
            input_data=input_data,
            recommendations=response.to_dict()
        )
    
    return RecommendationsResponse(
        recommendations=[
            SongResponse(**r.to_dict()) for r in response.recommendations
        ],
        input_type=response.input_type,
        session_id=response.session_id,
        is_continuation=response.is_continuation,
        used_chromadb=response.used_chromadb,
        chromadb_info=response.chromadb_info
    )


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit feedback (like/dislike) for a song recommendation.
    
    This feedback is used to improve future recommendations:
    - Liked songs inform the recommendation algorithm about preferences
    - Disliked songs are filtered out from future recommendations
    
    Requires authentication (registered user or guest).
    For guests, feedback is stored in the session but not persisted long-term.
    """
    if current_user.is_guest:
        # Guests can submit feedback but it's not persisted in ChromaDB
        return {
            "status": "noted",
            "message": "Feedback recorded for this session. Register to save preferences permanently.",
            "saved_to_chromadb": False
        }
    
    # For registered users, save to ChromaDB
    recommendation_service = get_recommendation_service()
    
    success = await recommendation_service.record_feedback(
        user_id=current_user.user_id,
        song_title=request.song_title,
        artist=request.artist,
        feedback_score=request.feedback_score,
        video_id=request.video_id,
        genre=request.genre,
        mood_tags=request.mood_tags
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save feedback"
        )
    
    return {
        "status": "saved",
        "message": "Feedback saved to your preferences.",
        "saved_to_chromadb": True
    }


@router.get("/history")
async def get_recommendation_history(
    limit: int = 10,
    include_recommendations: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the user's recommendation history.
    
    Returns recent recommendation queries and optionally their results.
    
    Args:
        limit: Maximum number of history items to return
        include_recommendations: If True, include the full recommendations in the response
    """
    user_service = UserService(db)
    
    history = await user_service.get_recommendation_history(
        user_id=current_user.user_id,
        session_id=current_user.session_id,
        limit=limit
    )
    
    result = []
    for h in history:
        item = {
            "id": str(h.id),
            "query_type": h.query_type,
            "input_data": h.input_data,
            "created_at": h.created_at.isoformat(),
            "recommendations_count": len(h.recommendations.get("songs", [])) if h.recommendations else 0
        }
        if include_recommendations:
            item["recommendations"] = h.recommendations
        result.append(item)
    
    return {"history": result}


@router.get("/history/{history_id}")
async def get_history_item(
    history_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific history item with its full recommendations.
    
    This allows users to resume a previous search session.
    """
    user_service = UserService(db)
    
    history_item = await user_service.get_history_item_by_id(
        history_id=history_id,
        user_id=current_user.user_id,
        session_id=current_user.session_id
    )
    
    if not history_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History item not found"
        )
    
    return {
        "id": str(history_item.id),
        "query_type": history_item.query_type,
        "input_data": history_item.input_data,
        "recommendations": history_item.recommendations,
        "created_at": history_item.created_at.isoformat()
    }


# Preferences endpoints

@router.get("/preferences/counts", response_model=PreferencesCountResponse)
async def get_preferences_counts(
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get counts of user's likes and dislikes.
    
    Requires authentication (registered user only, not guests).
    """
    if current_user.is_guest:
        return PreferencesCountResponse(likes=0, dislikes=0)
    
    chromadb = get_chromadb_client()
    counts = await chromadb.get_preferences_counts(current_user.user_id)
    
    return PreferencesCountResponse(
        likes=counts.get("likes", 0),
        dislikes=counts.get("dislikes", 0)
    )


@router.get("/preferences/likes", response_model=PreferencesResponse)
async def get_liked_songs(
    limit: int = 100,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get user's liked songs.
    
    Returns a list of songs the user has liked, with their IDs for deletion.
    Requires authentication (registered user only).
    """
    if current_user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guests cannot access preferences. Please register."
        )
    
    chromadb = get_chromadb_client()
    preferences = await chromadb.get_user_preferences_with_ids(
        user_id=current_user.user_id,
        preference_type="likes",
        limit=limit
    )
    
    return PreferencesResponse(
        preferences=[
            PreferenceItem(
                id=p["id"],
                song_title=p["song_title"],
                artist=p["artist"],
                genre=p.get("genre"),
                video_id=p.get("video_id"),
                mood_tags=p.get("mood_tags", [])
            )
            for p in preferences
        ],
        total=len(preferences),
        type="likes"
    )


@router.get("/preferences/dislikes", response_model=PreferencesResponse)
async def get_disliked_songs(
    limit: int = 100,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get user's disliked songs.
    
    Returns a list of songs the user has disliked (blocked), with their IDs for deletion.
    Disliked songs will never appear in recommendations.
    Requires authentication (registered user only).
    """
    if current_user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guests cannot access preferences. Please register."
        )
    
    chromadb = get_chromadb_client()
    preferences = await chromadb.get_user_preferences_with_ids(
        user_id=current_user.user_id,
        preference_type="dislikes",
        limit=limit
    )
    
    return PreferencesResponse(
        preferences=[
            PreferenceItem(
                id=p["id"],
                song_title=p["song_title"],
                artist=p["artist"],
                genre=p.get("genre"),
                video_id=p.get("video_id"),
                mood_tags=p.get("mood_tags", [])
            )
            for p in preferences
        ],
        total=len(preferences),
        type="dislikes"
    )


@router.delete("/preferences/{preference_type}/{preference_id}")
async def delete_preference(
    preference_type: str,
    preference_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Delete a specific preference (like or dislike).
    
    Args:
        preference_type: "likes" or "dislikes"
        preference_id: The ID of the preference to delete
        
    Requires authentication (registered user only).
    """
    if current_user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guests cannot modify preferences. Please register."
        )
    
    if preference_type not in ["likes", "dislikes"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="preference_type must be 'likes' or 'dislikes'"
        )
    
    chromadb = get_chromadb_client()
    success = await chromadb.delete_preference(
        user_id=current_user.user_id,
        preference_id=preference_id,
        preference_type=preference_type
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete preference"
        )
    
    return {
        "status": "deleted",
        "message": f"Preference removed from {preference_type}",
        "preference_id": preference_id
    }
