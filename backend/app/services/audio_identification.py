"""
Audio identification service using shazamio.

This module handles audio fingerprinting and song identification,
similar to Shazam's functionality.
"""
import os
import tempfile
import subprocess
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from shazamio import Shazam

logger = logging.getLogger(__name__)


@dataclass
class SongMetadata:
    """Metadata for an identified song."""
    title: str
    artist: str
    album: Optional[str] = None
    genre: Optional[str] = None
    release_year: Optional[str] = None
    shazam_id: Optional[str] = None
    cover_art_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    spotify_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_recommendation_input(self) -> Dict[str, str]:
        """Convert to input format for recommendation service."""
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album or "",
            "genre": self.genre or ""
        }


class AudioIdentificationService:
    """
    Service for identifying songs from audio samples.
    
    Uses shazamio library to perform audio fingerprinting
    and match against Shazam's database.
    """
    
    # Formats that need conversion to WAV for better recognition
    NEEDS_CONVERSION = {'webm', 'ogg', 'opus', 'm4a', 'aac'}
    
    def __init__(self):
        self.shazam = Shazam()
    
    def _convert_to_wav(self, input_path: str, output_path: str) -> bool:
        """
        Convert audio file to WAV format using ffmpeg.
        
        Args:
            input_path: Path to input audio file
            output_path: Path for output WAV file
            
        Returns:
            True if conversion successful, False otherwise
        """
        try:
            # Use ffmpeg to convert to WAV with optimal settings for Shazam
            # -ar 44100: Sample rate 44.1kHz (CD quality)
            # -ac 1: Mono channel (Shazam works with mono)
            # -acodec pcm_s16le: 16-bit PCM encoding
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output
                '-i', input_path,
                '-ar', '44100',
                '-ac', '1',
                '-acodec', 'pcm_s16le',
                '-t', '20',  # Limit to 20 seconds (enough for recognition)
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg conversion failed: {result.stderr}")
                return False
                
            return os.path.exists(output_path)
            
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg conversion timed out")
            return False
        except Exception as e:
            logger.error(f"FFmpeg conversion error: {e}")
            return False
    
    async def identify_from_bytes(
        self, 
        audio_bytes: bytes,
        file_extension: str = "wav"
    ) -> Optional[SongMetadata]:
        """
        Identify a song from audio bytes.
        
        Args:
            audio_bytes: Raw audio data
            file_extension: File extension (wav, mp3, etc.)
            
        Returns:
            SongMetadata if identified, None otherwise
        """
        ext = file_extension.lower().lstrip('.')
        temp_path = None
        converted_path = None
        
        try:
            # Write bytes to temp file (shazamio needs a file path)
            with tempfile.NamedTemporaryFile(
                suffix=f".{ext}", 
                delete=False
            ) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name
            
            # Check if format needs conversion
            if ext in self.NEEDS_CONVERSION:
                logger.info(f"Converting {ext} to WAV for better recognition")
                converted_path = temp_path.rsplit('.', 1)[0] + '_converted.wav'
                
                if self._convert_to_wav(temp_path, converted_path):
                    recognize_path = converted_path
                    logger.info("Conversion successful, using WAV file")
                else:
                    # Fallback to original if conversion fails
                    logger.warning("Conversion failed, trying original file")
                    recognize_path = temp_path
            else:
                recognize_path = temp_path
            
            # Attempt recognition with Shazam first
            logger.info(f"Attempting Shazam recognition on file: {recognize_path}")
            result = await self.shazam.recognize(recognize_path)
            
            if result:
                track = result.get("track")
                if track:
                    logger.info(f"Shazam identified: {track.get('title')} by {track.get('subtitle')}")
                    return self._parse_result(result)
                else:
                    logger.warning(f"Shazam returned result but no track data: {list(result.keys())}")
            else:
                logger.warning("Shazam returned empty result")
            
            # Song not identified - will fall back to CLAP audio analysis
            return None
            
        finally:
            # Clean up temp files
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            if converted_path and os.path.exists(converted_path):
                os.unlink(converted_path)
    
    async def identify_from_file(self, file_path: str) -> Optional[SongMetadata]:
        """
        Identify a song from a file path.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            SongMetadata if identified, None otherwise
        """
        result = await self.shazam.recognize(file_path)
        return self._parse_result(result)
    
    def _parse_result(self, result: Dict[str, Any]) -> Optional[SongMetadata]:
        """
        Parse Shazam API result into SongMetadata.
        
        Args:
            result: Raw result from shazamio
            
        Returns:
            SongMetadata or None if no match
        """
        if not result:
            return None
        
        track = result.get("track")
        if not track:
            return None
        
        # Extract basic info
        title = track.get("title", "Unknown")
        artist = track.get("subtitle", "Unknown Artist")
        
        # Extract album from sections
        album = None
        genre = None
        release_year = None
        
        sections = track.get("sections", [])
        for section in sections:
            if section.get("type") == "SONG":
                metadata = section.get("metadata", [])
                for meta in metadata:
                    label = meta.get("title", "").lower()
                    value = meta.get("text", "")
                    
                    if "album" in label:
                        album = value
                    elif "genre" in label:
                        genre = value
                    elif "released" in label or "year" in label:
                        release_year = value
        
        # Get cover art
        cover_art_url = None
        images = track.get("images", {})
        cover_art_url = images.get("coverart") or images.get("coverarthq")
        
        # Get streaming links
        apple_music_url = None
        spotify_url = None
        
        hub = track.get("hub", {})
        providers = hub.get("providers", [])
        for provider in providers:
            if provider.get("type") == "SPOTIFY":
                actions = provider.get("actions", [])
                for action in actions:
                    if action.get("type") == "uri":
                        spotify_url = action.get("uri")
            elif provider.get("type") == "APPLEMUSIC":
                actions = provider.get("actions", [])
                for action in actions:
                    if action.get("type") == "uri":
                        apple_music_url = action.get("uri")
        
        # Shazam ID
        shazam_id = track.get("key")
        
        return SongMetadata(
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            release_year=release_year,
            shazam_id=shazam_id,
            cover_art_url=cover_art_url,
            apple_music_url=apple_music_url,
            spotify_url=spotify_url
        )
    
    async def search_by_text(self, query: str, limit: int = 5) -> list[Dict[str, Any]]:
        """
        Search for songs by text query.
        
        Args:
            query: Search query (song name, artist, lyrics)
            limit: Maximum results to return
            
        Returns:
            List of matching tracks
        """
        results = await self.shazam.search_track(query=query, limit=limit)
        
        tracks = results.get("tracks", {}).get("hits", [])
        
        parsed_tracks = []
        for hit in tracks:
            track = hit.get("track", {})
            parsed_tracks.append({
                "title": track.get("title", "Unknown"),
                "artist": track.get("subtitle", "Unknown"),
                "shazam_id": track.get("key"),
                "cover_art_url": track.get("images", {}).get("coverart")
            })
        
        return parsed_tracks
    
    async def get_song_details(self, shazam_id: str) -> Optional[SongMetadata]:
        """
        Get detailed information about a song by Shazam ID.
        
        Args:
            shazam_id: The Shazam track key
            
        Returns:
            SongMetadata with full details
        """
        try:
            result = await self.shazam.track_about(track_id=int(shazam_id))
            
            if not result:
                return None
            
            # Parse similar to recognize result
            title = result.get("title", "Unknown")
            artist = result.get("subtitle", "Unknown Artist")
            
            # Get sections for metadata
            album = None
            genre = None
            
            sections = result.get("sections", [])
            for section in sections:
                if section.get("type") == "SONG":
                    metadata = section.get("metadata", [])
                    for meta in metadata:
                        label = meta.get("title", "").lower()
                        value = meta.get("text", "")
                        if "album" in label:
                            album = value
                        elif "genre" in label:
                            genre = value
            
            images = result.get("images", {})
            cover_art_url = images.get("coverart") or images.get("coverarthq")
            
            return SongMetadata(
                title=title,
                artist=artist,
                album=album,
                genre=genre,
                shazam_id=shazam_id,
                cover_art_url=cover_art_url
            )
        except Exception:
            return None


# Singleton instance
_audio_service: Optional[AudioIdentificationService] = None


def get_audio_service() -> AudioIdentificationService:
    """Get the audio identification service singleton."""
    global _audio_service
    if _audio_service is None:
        _audio_service = AudioIdentificationService()
    return _audio_service
