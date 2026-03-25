"""
YouTube Music routes for playlist management and song search.
"""
from typing import Optional, List
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.deps import get_current_user, CurrentUser
from app.services.user_service import UserService
from app.mcp.client import get_mcp_client


router = APIRouter()


# Request/Response Models

class YouTubeSongResponse(BaseModel):
    """Response model for a YouTube Music song."""
    video_id: str
    title: str
    artist: str
    album: Optional[str] = None
    duration: Optional[str] = None
    thumbnail_url: Optional[str] = None


class SearchResponse(BaseModel):
    """Response model for song search."""
    query: str
    total_results: int
    songs: List[YouTubeSongResponse]


class PlaylistResponse(BaseModel):
    """Response model for a playlist."""
    playlist_id: str
    title: str
    count: int = 0
    thumbnail_url: Optional[str] = None


class PlaylistsResponse(BaseModel):
    """Response model for user playlists."""
    total_playlists: int
    playlists: List[PlaylistResponse]


class AddToPlaylistRequest(BaseModel):
    """Request to add a song to a playlist."""
    video_id: str
    playlist_id: str


class CreatePlaylistRequest(BaseModel):
    """Request to create a new playlist."""
    title: str
    description: str = ""
    privacy_status: str = "PRIVATE"  # PUBLIC, PRIVATE, UNLISTED


class CreatePlaylistResponse(BaseModel):
    """Response for playlist creation."""
    success: bool
    playlist_id: str
    title: str


# Helper function to get YouTube auth

async def get_youtube_auth(
    current_user: CurrentUser,
    db: AsyncSession
) -> str:
    """Get YouTube Music authentication headers for the current user."""
    user_service = UserService(db)
    
    oauth = await user_service.get_decrypted_oauth_token(
        user_id=current_user.user_id,
        session_id=current_user.session_id,
        provider="youtube_music"
    )
    
    if not oauth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="YouTube Music not connected. Please authenticate first."
        )
    
    if oauth.get("is_expired"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="YouTube Music authentication expired. Please re-authenticate."
        )
    
    return oauth.get("access_token")


# Routes

@router.get("/search", response_model=SearchResponse)
async def search_youtube_music(
    query: str,
    limit: int = 10,
    current_user: Optional[CurrentUser] = Depends(get_current_user)
):
    """
    Search for songs on YouTube Music.
    
    Returns song results with video IDs that can be used for:
    - Playing on YouTube Music
    - Adding to playlists
    - Getting recommendations
    """
    if not query or len(query.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must be at least 2 characters"
        )
    
    mcp_client = get_mcp_client()
    
    try:
        songs = await mcp_client.search_songs(
            query=query,
            limit=min(limit, 50)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"YouTube Music search failed: {str(e)}"
        )
    
    return SearchResponse(
        query=query,
        total_results=len(songs),
        songs=[
            YouTubeSongResponse(
                video_id=s.video_id,
                title=s.title,
                artist=s.artist,
                album=s.album,
                duration=s.duration,
                thumbnail_url=s.thumbnail_url
            )
            for s in songs
        ]
    )


@router.get("/playlists", response_model=PlaylistsResponse)
async def get_user_playlists(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the authenticated user's YouTube Music playlists.
    
    Requires YouTube Music authentication.
    """
    auth_headers = await get_youtube_auth(current_user, db)
    mcp_client = get_mcp_client()
    
    try:
        playlists = await mcp_client.get_user_playlists(auth_headers)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get playlists: {str(e)}"
        )
    
    return PlaylistsResponse(
        total_playlists=len(playlists),
        playlists=[
            PlaylistResponse(
                playlist_id=p.playlist_id,
                title=p.title,
                count=p.count,
                thumbnail_url=p.thumbnail_url
            )
            for p in playlists
        ]
    )


@router.post("/playlists", response_model=CreatePlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    request: CreatePlaylistRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new YouTube Music playlist.
    
    Requires YouTube Music authentication.
    """
    auth_headers = await get_youtube_auth(current_user, db)
    mcp_client = get_mcp_client()
    
    try:
        playlist_id = await mcp_client.create_playlist(
            title=request.title,
            auth_headers=auth_headers,
            description=request.description,
            privacy_status=request.privacy_status
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create playlist: {str(e)}"
        )
    
    return CreatePlaylistResponse(
        success=True,
        playlist_id=playlist_id,
        title=request.title
    )


@router.post("/playlists/add")
async def add_to_playlist(
    request: AddToPlaylistRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a song to a YouTube Music playlist.
    
    Requires YouTube Music authentication.
    """
    auth_headers = await get_youtube_auth(current_user, db)
    mcp_client = get_mcp_client()
    
    try:
        success = await mcp_client.add_to_playlist(
            video_id=request.video_id,
            playlist_id=request.playlist_id,
            auth_headers=auth_headers
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add to playlist: {str(e)}"
        )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add song to playlist"
        )
    
    return {
        "success": True,
        "message": f"Song {request.video_id} added to playlist {request.playlist_id}"
    }


@router.get("/song/{video_id}")
async def get_song_details(
    video_id: str,
    current_user: Optional[CurrentUser] = Depends(get_current_user)
):
    """
    Get detailed information about a song by video ID.
    """
    mcp_client = get_mcp_client()
    
    try:
        details = await mcp_client.get_song_details(video_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get song details: {str(e)}"
        )
    
    return details


@router.get("/recommendations/{video_id}", response_model=SearchResponse)
async def get_youtube_recommendations(
    video_id: str,
    limit: int = 10,
    current_user: Optional[CurrentUser] = Depends(get_current_user)
):
    """
    Get YouTube Music's recommendations for a song.
    
    These are YouTube's native recommendations, separate from our AI recommendations.
    """
    mcp_client = get_mcp_client()
    
    try:
        songs = await mcp_client.get_recommendations(
            video_id=video_id,
            limit=min(limit, 25)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(e)}"
        )
    
    return SearchResponse(
        query=f"similar to {video_id}",
        total_results=len(songs),
        songs=[
            YouTubeSongResponse(
                video_id=s.video_id,
                title=s.title,
                artist=s.artist,
                album=s.album,
                duration=s.duration,
                thumbnail_url=s.thumbnail_url
            )
            for s in songs
        ]
    )
