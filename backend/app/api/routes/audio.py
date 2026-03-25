"""
Audio routes for song identification and analysis.

Includes:
- Song identification via Shazam
- Audio analysis via CLAP for unidentified songs
"""
import logging
from typing import Optional, List
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File

from app.api.deps import get_current_user_optional, CurrentUser
from app.services.audio_identification import get_audio_service
from app.services.audio_analysis import analyze_audio, get_search_queries_from_audio
from app.mcp.client import MCPYouTubeMusicClient

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models

class AudioAnalysisResult(BaseModel):
    """Audio analysis result when song is not identified."""
    mood_tags: List[str] = []
    genre_tags: List[str] = []
    tempo_description: str = "moderate"
    energy_level: str = "medium"
    search_queries: List[str] = []  # Pre-generated queries for YouTube Music


class SongIdentificationResponse(BaseModel):
    """Response model for song identification."""
    identified: bool
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    release_year: Optional[str] = None
    cover_art_url: Optional[str] = None
    shazam_id: Optional[str] = None
    apple_music_url: Optional[str] = None
    spotify_url: Optional[str] = None
    video_id: Optional[str] = None  # YouTube Music video ID for playback
    thumbnail_url: Optional[str] = None  # YouTube thumbnail
    message: Optional[str] = None
    # Audio analysis (for unidentified songs - Case 3)
    audio_analysis: Optional[AudioAnalysisResult] = None


class SearchResult(BaseModel):
    """Search result model."""
    title: str
    artist: str
    shazam_id: Optional[str] = None
    cover_art_url: Optional[str] = None


class SearchResponse(BaseModel):
    """Response model for song search."""
    query: str
    results: list[SearchResult]


# Routes

@router.post("/identify", response_model=SongIdentificationResponse)
async def identify_audio(
    audio_file: UploadFile = File(...),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional)
):
    """
    Identify a song from an audio file.
    
    Upload an audio file (WAV, MP3, etc.) and the service will attempt
    to identify the song using Shazam's audio fingerprinting technology.
    
    The identified song metadata can then be used to get AI recommendations
    via the /recommendations/audio endpoint.
    
    Supported formats: WAV, MP3, M4A, FLAC, OGG
    Recommended: At least 5-10 seconds of clear audio
    """
    # Validate file type
    allowed_types = [
        "audio/wav", "audio/wave", "audio/x-wav",
        "audio/mpeg", "audio/mp3",
        "audio/m4a", "audio/x-m4a", "audio/mp4",
        "audio/flac", "audio/x-flac",
        "audio/ogg", "audio/vorbis",
        "audio/webm", "audio/opus"  # Browser recording formats
    ]
    
    content_type = audio_file.content_type or ""
    if content_type not in allowed_types and not content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format: {content_type}. Supported: WAV, MP3, M4A, FLAC, OGG"
        )
    
    # Read file content
    try:
        audio_bytes = await audio_file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read audio file: {str(e)}"
        )
    
    # Check file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    if len(audio_bytes) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file too large. Maximum size is 10MB."
        )
    
    # Determine file extension
    filename = audio_file.filename or "audio.wav"
    extension = filename.rsplit(".", 1)[-1] if "." in filename else "wav"
    
    # Identify song
    audio_service = get_audio_service()
    
    try:
        result = await audio_service.identify_from_bytes(audio_bytes, extension)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio identification failed: {str(e)}"
        )
    
    if not result:
        # CASE 3: Song not identified - analyze audio for mood/genre
        logger.info("Song not identified, running audio analysis...")
        
        audio_analysis_result = None
        try:
            analysis = await analyze_audio(audio_bytes)
            if analysis:
                search_queries = await get_search_queries_from_audio(audio_bytes)
                audio_analysis_result = AudioAnalysisResult(
                    mood_tags=analysis.mood_tags,
                    genre_tags=analysis.genre_tags,
                    tempo_description=analysis.tempo_description,
                    energy_level=analysis.energy_level,
                    search_queries=search_queries
                )
                logger.info(f"Audio analysis: mood={analysis.mood_tags}, genre={analysis.genre_tags}")
        except Exception as e:
            logger.warning(f"Audio analysis failed: {e}")
        
        return SongIdentificationResponse(
            identified=False,
            message="Could not identify the song, but we analyzed its characteristics.",
            audio_analysis=audio_analysis_result
        )
    
    # Search YouTube Music to get video_id for playback
    video_id = None
    thumbnail_url = None
    try:
        yt_client = MCPYouTubeMusicClient()
        search_query = f"{result.title} {result.artist}"
        yt_results = await yt_client.search_songs(search_query, limit=1)
        if yt_results:
            video_id = yt_results[0].video_id or None
            thumbnail_url = yt_results[0].thumbnail_url
            logger.info(f"Found YouTube video for '{result.title}': {video_id}")
    except Exception as e:
        logger.warning(f"Failed to get YouTube video_id: {e}")
    
    return SongIdentificationResponse(
        identified=True,
        title=result.title,
        artist=result.artist,
        album=result.album,
        genre=result.genre,
        release_year=result.release_year,
        cover_art_url=result.cover_art_url or thumbnail_url,
        shazam_id=result.shazam_id,
        apple_music_url=result.apple_music_url,
        spotify_url=result.spotify_url,
        video_id=video_id,
        thumbnail_url=thumbnail_url
    )


@router.get("/search", response_model=SearchResponse)
async def search_songs(
    query: str,
    limit: int = 5
):
    """
    Search for songs by text query.
    
    Search by song name, artist, or lyrics snippet.
    Returns basic metadata for matching songs.
    """
    if not query or len(query.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must be at least 2 characters"
        )
    
    audio_service = get_audio_service()
    
    try:
        results = await audio_service.search_by_text(query, limit=min(limit, 20))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
    
    return SearchResponse(
        query=query,
        results=[
            SearchResult(
                title=r.get("title", "Unknown"),
                artist=r.get("artist", "Unknown"),
                shazam_id=r.get("shazam_id"),
                cover_art_url=r.get("cover_art_url")
            )
            for r in results
        ]
    )


@router.get("/details/{shazam_id}", response_model=SongIdentificationResponse)
async def get_song_details(shazam_id: str):
    """
    Get detailed information about a song by Shazam ID.
    
    Use the shazam_id returned from /identify or /search endpoints.
    """
    audio_service = get_audio_service()
    
    try:
        result = await audio_service.get_song_details(shazam_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get song details: {str(e)}"
        )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found"
        )
    
    return SongIdentificationResponse(
        identified=True,
        title=result.title,
        artist=result.artist,
        album=result.album,
        genre=result.genre,
        cover_art_url=result.cover_art_url,
        shazam_id=result.shazam_id
    )
