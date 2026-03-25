"""
MCP Client Orchestrator for YouTube Music integration.

This module provides a client that communicates with the YouTube Music MCP server,
allowing the backend to invoke YouTube Music tools through the Model Context Protocol.
"""
import os
import sys
import json
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from contextlib import asynccontextmanager

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

from app.core.config import settings


@dataclass
class YouTubeMusicSong:
    """Represents a song from YouTube Music."""
    video_id: str
    title: str
    artist: str
    album: Optional[str] = None
    duration: Optional[str] = None
    thumbnail_url: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "YouTubeMusicSong":
        return cls(
            video_id=data.get("video_id", ""),
            title=data.get("title", "Unknown"),
            artist=data.get("artist", "Unknown"),
            album=data.get("album"),
            duration=data.get("duration"),
            thumbnail_url=data.get("thumbnail_url")
        )


@dataclass
class Playlist:
    """Represents a YouTube Music playlist."""
    playlist_id: str
    title: str
    count: int = 0
    thumbnail_url: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Playlist":
        return cls(
            playlist_id=data.get("playlist_id", ""),
            title=data.get("title", "Unknown"),
            count=data.get("count", 0),
            thumbnail_url=data.get("thumbnail_url")
        )


class MCPYouTubeMusicClient:
    """
    Client for invoking YouTube Music tools via MCP.
    
    This client spawns the MCP server as a subprocess and communicates
    with it using stdio (stdin/stdout).
    """
    
    def __init__(self):
        self.server_path = settings.MCP_YTMUSIC_SERVER_PATH
        self._session: Optional[ClientSession] = None
    
    @asynccontextmanager
    async def _get_session(self):
        """
        Context manager for MCP session.
        
        Creates a new session for each operation to ensure clean state.
        """
        # Get the Python executable path
        python_executable = sys.executable
        
        # Server parameters
        server_params = StdioServerParameters(
            command=python_executable,
            args=["-m", "app.mcp.youtube_music_server"],
            env={
                **os.environ,
                "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            }
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    
    async def _invoke_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Invoke an MCP tool and return the result.
        
        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool arguments
            
        Returns:
            Tool result as a dictionary
        """
        async with self._get_session() as session:
            result = await session.call_tool(tool_name, arguments)
            
            # Parse the text content
            if result.content and len(result.content) > 0:
                text_content = result.content[0]
                if hasattr(text_content, 'text'):
                    return json.loads(text_content.text)
            
            return {"error": "No response from tool"}
    
    async def search_songs(
        self, 
        query: str, 
        limit: int = 10,
        auth_headers: Optional[str] = None
    ) -> List[YouTubeMusicSong]:
        """
        Search for songs on YouTube Music.
        
        Args:
            query: Search query (song name, artist, etc.)
            limit: Maximum number of results
            auth_headers: Optional authentication headers
            
        Returns:
            List of matching songs
        """
        arguments = {
            "query": query,
            "limit": limit
        }
        if auth_headers:
            arguments["auth_headers"] = auth_headers
        
        result = await self._invoke_tool("search_songs", arguments)
        
        if "error" in result:
            raise Exception(result["error"])
        
        return [
            YouTubeMusicSong.from_dict(song) 
            for song in result.get("songs", [])
        ]
    
    async def get_song_details(
        self, 
        video_id: str,
        auth_headers: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed information about a song.
        
        Args:
            video_id: YouTube video ID
            auth_headers: Optional authentication headers
            
        Returns:
            Song details dictionary
        """
        arguments = {"video_id": video_id}
        if auth_headers:
            arguments["auth_headers"] = auth_headers
        
        result = await self._invoke_tool("get_song_details", arguments)
        
        if "error" in result:
            raise Exception(result["error"])
        
        return result
    
    async def get_user_playlists(
        self, 
        auth_headers: str
    ) -> List[Playlist]:
        """
        Get the authenticated user's playlists.
        
        Args:
            auth_headers: Authentication headers (required)
            
        Returns:
            List of user's playlists
        """
        result = await self._invoke_tool(
            "get_user_playlists", 
            {"auth_headers": auth_headers}
        )
        
        if "error" in result:
            raise Exception(result["error"])
        
        return [
            Playlist.from_dict(p) 
            for p in result.get("playlists", [])
        ]
    
    async def add_to_playlist(
        self, 
        video_id: str, 
        playlist_id: str,
        auth_headers: str
    ) -> bool:
        """
        Add a song to a playlist.
        
        Args:
            video_id: YouTube video ID
            playlist_id: Target playlist ID
            auth_headers: Authentication headers (required)
            
        Returns:
            True if successful
        """
        result = await self._invoke_tool(
            "add_to_playlist",
            {
                "video_id": video_id,
                "playlist_id": playlist_id,
                "auth_headers": auth_headers
            }
        )
        
        if "error" in result:
            raise Exception(result["error"])
        
        return result.get("success", False)
    
    async def create_playlist(
        self,
        title: str,
        auth_headers: str,
        description: str = "",
        privacy_status: str = "PRIVATE"
    ) -> str:
        """
        Create a new playlist.
        
        Args:
            title: Playlist title
            auth_headers: Authentication headers (required)
            description: Playlist description
            privacy_status: Privacy status (PUBLIC, PRIVATE, UNLISTED)
            
        Returns:
            ID of the created playlist
        """
        result = await self._invoke_tool(
            "create_playlist",
            {
                "title": title,
                "description": description,
                "privacy_status": privacy_status,
                "auth_headers": auth_headers
            }
        )
        
        if "error" in result:
            raise Exception(result["error"])
        
        return result.get("playlist_id", "")
    
    async def get_recommendations(
        self,
        video_id: str,
        limit: int = 10,
        auth_headers: Optional[str] = None
    ) -> List[YouTubeMusicSong]:
        """
        Get song recommendations based on a video.
        
        Args:
            video_id: YouTube video ID
            limit: Maximum number of recommendations
            auth_headers: Optional authentication headers
            
        Returns:
            List of recommended songs
        """
        arguments = {
            "video_id": video_id,
            "limit": limit
        }
        if auth_headers:
            arguments["auth_headers"] = auth_headers
        
        result = await self._invoke_tool("get_song_recommendations", arguments)
        
        if "error" in result:
            raise Exception(result["error"])
        
        return [
            YouTubeMusicSong.from_dict(song)
            for song in result.get("songs", [])
        ]
    
    async def enrich_songs_with_youtube_data(
        self,
        songs: List[Dict[str, str]],
        auth_headers: Optional[str] = None
    ) -> List[YouTubeMusicSong]:
        """
        Enrich a list of song recommendations with YouTube Music data.
        
        Takes song recommendations from Ollama (title + artist) and finds
        matching videos on YouTube Music.
        
        Args:
            songs: List of dicts with 'title' and 'artist' keys
            auth_headers: Optional authentication headers
            
        Returns:
            List of enriched songs with video IDs and thumbnails
        """
        enriched = []
        
        for song in songs:
            query = f"{song.get('title', '')} {song.get('artist', '')}"
            try:
                results = await self.search_songs(query, limit=1, auth_headers=auth_headers)
                if results:
                    enriched.append(results[0])
                else:
                    # Create a placeholder if no match found
                    enriched.append(YouTubeMusicSong(
                        video_id="",
                        title=song.get('title', 'Unknown'),
                        artist=song.get('artist', 'Unknown')
                    ))
            except Exception:
                # On error, create placeholder
                enriched.append(YouTubeMusicSong(
                    video_id="",
                    title=song.get('title', 'Unknown'),
                    artist=song.get('artist', 'Unknown')
                ))
        
        return enriched


# Singleton instance
_mcp_client: Optional[MCPYouTubeMusicClient] = None


def get_mcp_client() -> MCPYouTubeMusicClient:
    """Get the MCP YouTube Music client singleton."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPYouTubeMusicClient()
    return _mcp_client
