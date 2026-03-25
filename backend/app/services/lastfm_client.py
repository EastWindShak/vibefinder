"""
Last.fm API client for getting song tags and similar tracks.

This service enriches song metadata with community tags like mood, genre, etc.
"""

import logging
import aiohttp
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LastFmTrackInfo:
    """Track information from Last.fm."""
    name: str
    artist: str
    tags: List[str]  # e.g., ["sensual", "R&B", "slow", "romantic"]
    similar_tracks: List[Dict[str, str]]  # [{"name": "...", "artist": "..."}]
    listeners: int = 0
    playcount: int = 0


class LastFmClient:
    """
    Client for Last.fm API.
    
    Provides methods to get track tags and similar tracks.
    API docs: https://www.last.fm/api
    """
    
    BASE_URL = "http://ws.audioscrobbler.com/2.0/"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.LASTFM_API_KEY
        if not self.api_key:
            logger.warning("Last.fm API key not configured - service will be disabled")
    
    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)
    
    async def _make_request(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a request to Last.fm API."""
        if not self.is_configured:
            return None
        
        params.update({
            "api_key": self.api_key,
            "format": "json"
        })
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"Last.fm API returned {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Last.fm API error: {e}")
            return None
    
    async def get_track_info(self, track: str, artist: str) -> Optional[LastFmTrackInfo]:
        """
        Get track information including tags.
        
        Args:
            track: Track name
            artist: Artist name
            
        Returns:
            LastFmTrackInfo with tags and metadata, or None if not found
        """
        data = await self._make_request({
            "method": "track.getInfo",
            "track": track,
            "artist": artist,
            "autocorrect": 1
        })
        
        if not data or "track" not in data:
            return None
        
        track_data = data["track"]
        
        # Extract tags
        tags = []
        if "toptags" in track_data and "tag" in track_data["toptags"]:
            tag_list = track_data["toptags"]["tag"]
            if isinstance(tag_list, list):
                tags = [t["name"].lower() for t in tag_list[:10]]
            elif isinstance(tag_list, dict):
                tags = [tag_list["name"].lower()]
        
        return LastFmTrackInfo(
            name=track_data.get("name", track),
            artist=track_data.get("artist", {}).get("name", artist) if isinstance(track_data.get("artist"), dict) else artist,
            tags=tags,
            similar_tracks=[],
            listeners=int(track_data.get("listeners", 0)),
            playcount=int(track_data.get("playcount", 0))
        )
    
    async def get_track_tags(self, track: str, artist: str) -> List[str]:
        """
        Get just the tags for a track.
        
        Args:
            track: Track name
            artist: Artist name
            
        Returns:
            List of tag strings, empty if not found
        """
        info = await self.get_track_info(track, artist)
        return info.tags if info else []
    
    async def get_similar_tracks(self, track: str, artist: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Get similar tracks from Last.fm.
        
        Args:
            track: Track name
            artist: Artist name
            limit: Maximum number of similar tracks
            
        Returns:
            List of {"name": ..., "artist": ...} dicts
        """
        data = await self._make_request({
            "method": "track.getSimilar",
            "track": track,
            "artist": artist,
            "limit": limit,
            "autocorrect": 1
        })
        
        if not data or "similartracks" not in data:
            return []
        
        similar = data["similartracks"].get("track", [])
        if not isinstance(similar, list):
            similar = [similar] if similar else []
        
        return [
            {
                "name": t.get("name", ""),
                "artist": t.get("artist", {}).get("name", "") if isinstance(t.get("artist"), dict) else ""
            }
            for t in similar[:limit]
            if t.get("name")
        ]
    
    async def get_artist_tags(self, artist: str) -> List[str]:
        """
        Get tags for an artist (fallback if track tags not available).
        
        Args:
            artist: Artist name
            
        Returns:
            List of tag strings
        """
        data = await self._make_request({
            "method": "artist.getTopTags",
            "artist": artist,
            "autocorrect": 1
        })
        
        if not data or "toptags" not in data:
            return []
        
        tags = data["toptags"].get("tag", [])
        if not isinstance(tags, list):
            tags = [tags] if tags else []
        
        return [t["name"].lower() for t in tags[:10] if t.get("name")]


# Singleton instance
_lastfm_client: Optional[LastFmClient] = None


def get_lastfm_client() -> LastFmClient:
    """Get or create the Last.fm client singleton."""
    global _lastfm_client
    if _lastfm_client is None:
        _lastfm_client = LastFmClient()
    return _lastfm_client
