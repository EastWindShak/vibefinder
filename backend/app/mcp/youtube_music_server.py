#!/usr/bin/env python3
"""
MCP Server for YouTube Music integration.

This server exposes YouTube Music functionality via the Model Context Protocol,
allowing the LLM to search for songs, get details, and manage playlists.

Run as a standalone server:
    python -m app.mcp.youtube_music_server

The server expects authentication headers to be passed via environment variables
or through tool arguments.
"""
import os
import sys
import json
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

# MCP imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# YouTube Music API
from ytmusicapi import YTMusic


@dataclass
class SongResult:
    """Represents a song search result."""
    video_id: str
    title: str
    artist: str
    album: Optional[str] = None
    duration: Optional[str] = None
    thumbnail_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "duration": self.duration,
            "thumbnail_url": self.thumbnail_url
        }


class YouTubeMusicMCPServer:
    """MCP Server implementation for YouTube Music."""
    
    def __init__(self):
        self.server = Server("youtube-music-server")
        self.ytmusic: Optional[YTMusic] = None
        self._setup_handlers()
    
    def _get_ytmusic(self, auth_headers: Optional[str] = None) -> YTMusic:
        """
        Get or create YTMusic instance.
        
        Args:
            auth_headers: JSON string of authentication headers, or path to headers file
        """
        if auth_headers:
            # If it's a file path
            if os.path.exists(auth_headers):
                return YTMusic(auth_headers)
            # If it's a JSON string
            try:
                headers = json.loads(auth_headers)
                # Write to temp file for YTMusic
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(headers, f)
                    temp_path = f.name
                return YTMusic(temp_path)
            except json.JSONDecodeError:
                pass
        
        # Try environment variable
        env_headers = os.environ.get("YTMUSIC_AUTH_HEADERS")
        if env_headers:
            if os.path.exists(env_headers):
                return YTMusic(env_headers)
            try:
                headers = json.loads(env_headers)
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(headers, f)
                    temp_path = f.name
                return YTMusic(temp_path)
            except json.JSONDecodeError:
                pass
        
        # Return unauthenticated instance (limited functionality)
        return YTMusic()
    
    def _setup_handlers(self):
        """Set up MCP tool handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """Return list of available tools."""
            return [
                Tool(
                    name="search_songs",
                    description="Search for songs on YouTube Music",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (song name, artist, etc.)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 10)",
                                "default": 10
                            },
                            "auth_headers": {
                                "type": "string",
                                "description": "Optional authentication headers JSON or file path"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_song_details",
                    description="Get detailed information about a specific song",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "video_id": {
                                "type": "string",
                                "description": "YouTube video ID of the song"
                            },
                            "auth_headers": {
                                "type": "string",
                                "description": "Optional authentication headers JSON or file path"
                            }
                        },
                        "required": ["video_id"]
                    }
                ),
                Tool(
                    name="get_user_playlists",
                    description="Get the authenticated user's playlists",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "auth_headers": {
                                "type": "string",
                                "description": "Authentication headers JSON or file path (required)"
                            }
                        },
                        "required": ["auth_headers"]
                    }
                ),
                Tool(
                    name="add_to_playlist",
                    description="Add a song to a playlist",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "video_id": {
                                "type": "string",
                                "description": "YouTube video ID of the song to add"
                            },
                            "playlist_id": {
                                "type": "string",
                                "description": "ID of the playlist to add the song to"
                            },
                            "auth_headers": {
                                "type": "string",
                                "description": "Authentication headers JSON or file path (required)"
                            }
                        },
                        "required": ["video_id", "playlist_id", "auth_headers"]
                    }
                ),
                Tool(
                    name="create_playlist",
                    description="Create a new playlist",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Playlist title"
                            },
                            "description": {
                                "type": "string",
                                "description": "Playlist description",
                                "default": ""
                            },
                            "privacy_status": {
                                "type": "string",
                                "description": "Privacy status: PUBLIC, PRIVATE, or UNLISTED",
                                "default": "PRIVATE"
                            },
                            "auth_headers": {
                                "type": "string",
                                "description": "Authentication headers JSON or file path (required)"
                            }
                        },
                        "required": ["title", "auth_headers"]
                    }
                ),
                Tool(
                    name="get_song_recommendations",
                    description="Get song recommendations based on a video ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "video_id": {
                                "type": "string",
                                "description": "YouTube video ID to get recommendations for"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of recommendations (default: 10)",
                                "default": 10
                            },
                            "auth_headers": {
                                "type": "string",
                                "description": "Optional authentication headers"
                            }
                        },
                        "required": ["video_id"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool invocations."""
            try:
                auth_headers = arguments.get("auth_headers")
                ytmusic = self._get_ytmusic(auth_headers)
                
                if name == "search_songs":
                    result = await self._search_songs(
                        ytmusic,
                        arguments["query"],
                        arguments.get("limit", 10)
                    )
                elif name == "get_song_details":
                    result = await self._get_song_details(
                        ytmusic,
                        arguments["video_id"]
                    )
                elif name == "get_user_playlists":
                    result = await self._get_user_playlists(ytmusic)
                elif name == "add_to_playlist":
                    result = await self._add_to_playlist(
                        ytmusic,
                        arguments["video_id"],
                        arguments["playlist_id"]
                    )
                elif name == "create_playlist":
                    result = await self._create_playlist(
                        ytmusic,
                        arguments["title"],
                        arguments.get("description", ""),
                        arguments.get("privacy_status", "PRIVATE")
                    )
                elif name == "get_song_recommendations":
                    result = await self._get_recommendations(
                        ytmusic,
                        arguments["video_id"],
                        arguments.get("limit", 10)
                    )
                else:
                    result = {"error": f"Unknown tool: {name}"}
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)})
                )]
    
    async def _search_songs(
        self, 
        ytmusic: YTMusic, 
        query: str, 
        limit: int
    ) -> Dict[str, Any]:
        """Search for songs on YouTube Music."""
        results = ytmusic.search(query, filter="songs", limit=limit)
        
        songs = []
        for item in results:
            if item.get("resultType") == "song":
                artists = item.get("artists", [])
                artist_name = artists[0]["name"] if artists else "Unknown Artist"
                
                song = SongResult(
                    video_id=item.get("videoId", ""),
                    title=item.get("title", "Unknown"),
                    artist=artist_name,
                    album=item.get("album", {}).get("name") if item.get("album") else None,
                    duration=item.get("duration"),
                    thumbnail_url=item.get("thumbnails", [{}])[-1].get("url") if item.get("thumbnails") else None
                )
                songs.append(song.to_dict())
        
        return {
            "query": query,
            "total_results": len(songs),
            "songs": songs
        }
    
    async def _get_song_details(
        self, 
        ytmusic: YTMusic, 
        video_id: str
    ) -> Dict[str, Any]:
        """Get detailed information about a song."""
        try:
            song = ytmusic.get_song(video_id)
            
            video_details = song.get("videoDetails", {})
            
            return {
                "video_id": video_id,
                "title": video_details.get("title", "Unknown"),
                "artist": video_details.get("author", "Unknown"),
                "duration_seconds": video_details.get("lengthSeconds"),
                "view_count": video_details.get("viewCount"),
                "thumbnail_url": video_details.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url"),
                "description": video_details.get("shortDescription", "")
            }
        except Exception as e:
            return {"error": f"Failed to get song details: {str(e)}"}
    
    async def _get_user_playlists(self, ytmusic: YTMusic) -> Dict[str, Any]:
        """Get user's playlists."""
        try:
            playlists = ytmusic.get_library_playlists()
            
            return {
                "total_playlists": len(playlists),
                "playlists": [
                    {
                        "playlist_id": p.get("playlistId", ""),
                        "title": p.get("title", "Unknown"),
                        "count": p.get("count", 0),
                        "thumbnail_url": p.get("thumbnails", [{}])[-1].get("url") if p.get("thumbnails") else None
                    }
                    for p in playlists
                ]
            }
        except Exception as e:
            return {"error": f"Failed to get playlists: {str(e)}"}
    
    async def _add_to_playlist(
        self, 
        ytmusic: YTMusic, 
        video_id: str, 
        playlist_id: str
    ) -> Dict[str, Any]:
        """Add a song to a playlist."""
        try:
            result = ytmusic.add_playlist_items(playlist_id, [video_id])
            
            return {
                "success": True,
                "message": f"Added song {video_id} to playlist {playlist_id}",
                "result": result
            }
        except Exception as e:
            return {"error": f"Failed to add to playlist: {str(e)}"}
    
    async def _create_playlist(
        self,
        ytmusic: YTMusic,
        title: str,
        description: str,
        privacy_status: str
    ) -> Dict[str, Any]:
        """Create a new playlist."""
        try:
            playlist_id = ytmusic.create_playlist(
                title=title,
                description=description,
                privacy_status=privacy_status
            )
            
            return {
                "success": True,
                "playlist_id": playlist_id,
                "title": title
            }
        except Exception as e:
            return {"error": f"Failed to create playlist: {str(e)}"}
    
    async def _get_recommendations(
        self,
        ytmusic: YTMusic,
        video_id: str,
        limit: int
    ) -> Dict[str, Any]:
        """Get song recommendations based on a video."""
        try:
            # Get watch playlist which contains related songs
            watch = ytmusic.get_watch_playlist(video_id, limit=limit + 5)
            
            tracks = watch.get("tracks", [])[:limit]
            
            songs = []
            for track in tracks:
                artists = track.get("artists", [])
                artist_name = artists[0]["name"] if artists else "Unknown Artist"
                
                songs.append({
                    "video_id": track.get("videoId", ""),
                    "title": track.get("title", "Unknown"),
                    "artist": artist_name,
                    "album": track.get("album", {}).get("name") if track.get("album") else None,
                    "duration": track.get("duration"),
                    "thumbnail_url": track.get("thumbnail", [{}])[-1].get("url") if track.get("thumbnail") else None
                })
            
            return {
                "based_on": video_id,
                "total_recommendations": len(songs),
                "songs": songs
            }
        except Exception as e:
            return {"error": f"Failed to get recommendations: {str(e)}"}
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Entry point for the MCP server."""
    server = YouTubeMusicMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
