"""
Ollama client for LLM-based music recommendations.

This module handles communication with the local Ollama instance
running the llama3 model for generating music recommendations.
"""
import json
import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import ollama
from ollama import AsyncClient

from app.core.config import settings

# Langfuse for LLM observability
try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None

logger = logging.getLogger(__name__)


@dataclass
class SongRecommendation:
    """Represents a song recommendation from the LLM."""
    title: str
    artist: str
    reason: Optional[str] = None
    genre: Optional[str] = None
    mood: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "artist": self.artist,
            "reason": self.reason,
            "genre": self.genre,
            "mood": self.mood
        }


class OllamaClient:
    """
    Client for generating music recommendations using Ollama.
    
    Uses the llama3 model to analyze user input (mood or identified song)
    and generate relevant music recommendations.
    
    Integrates with Langfuse for observability and prompt management.
    """
    
    def __init__(self):
        self.model = settings.OLLAMA_MODEL
        self.base_url = settings.OLLAMA_BASE_URL
        self.client = AsyncClient(host=self.base_url)
        
        # Initialize Langfuse for observability
        self.langfuse = None
        if LANGFUSE_AVAILABLE and settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
            try:
                self.langfuse = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST
                )
                logger.info(f"Langfuse initialized - host: {settings.LANGFUSE_HOST}")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse: {e}")
                self.langfuse = None
        else:
            logger.info("Langfuse not configured (missing keys or package)")
    
    async def generate_recommendations(
        self,
        system_prompt: str,
        user_prompt: str,
        num_recommendations: int = 10,
        trace_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SongRecommendation]:
        """
        Generate music recommendations based on the prompts.
        
        Args:
            system_prompt: The system context (varies by user type)
            user_prompt: The user's input (mood or song info)
            num_recommendations: Number of songs to recommend
            trace_metadata: Optional metadata for Langfuse tracing
            
        Returns:
            List of song recommendations
        """
        # Build the full prompt
        full_user_prompt = f"""
{user_prompt}

Please recommend exactly {num_recommendations} songs. For each song, provide:
1. Song title
2. Artist name
3. Brief reason why this song fits
4. Genre
5. Mood/vibe of the song

Format your response as a JSON array with objects containing these fields:
"title", "artist", "reason", "genre", "mood"

Respond ONLY with the JSON array, no additional text.
"""
        
        # Start Langfuse trace if available (v2 API)
        trace = None
        generation = None
        if self.langfuse:
            try:
                trace = self.langfuse.trace(
                    name="generate_recommendations",
                    metadata=trace_metadata or {}
                )
                generation = trace.generation(
                    name="ollama_chat",
                    model=self.model,
                    input={
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": full_user_prompt}
                        ]
                    },
                    model_parameters={
                        "temperature": 0.8,
                        "top_p": 0.9
                    }
                )
            except Exception as e:
                logger.warning(f"Langfuse trace error: {e}")
        
        try:
            response = await self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_user_prompt}
                ],
                options={
                    "temperature": 0.8,
                    "top_p": 0.9,
                }
            )
            
            # Extract the response content
            content = response.get("message", {}).get("content", "")
            
            # Parse the JSON response
            recommendations = self._parse_recommendations(content)
            
            # End Langfuse generation
            if generation:
                try:
                    generation.end(
                        output=content,
                        usage={
                            "prompt_tokens": response.get("prompt_eval_count", 0),
                            "completion_tokens": response.get("eval_count", 0)
                        },
                        metadata={
                            "recommendations_count": len(recommendations),
                            "success": True
                        }
                    )
                except Exception as e:
                    logger.warning(f"Langfuse generation end error: {e}")
            
            return recommendations
        
        except Exception as e:
            # End Langfuse generation with error
            if generation:
                try:
                    generation.end(
                        output=str(e),
                        level="ERROR",
                        metadata={"success": False}
                    )
                except Exception:
                    pass
            
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    def _parse_recommendations(self, content: str) -> List[SongRecommendation]:
        """
        Parse LLM response into SongRecommendation objects.
        
        Handles various response formats and attempts to extract
        valid recommendations.
        """
        recommendations = []
        
        # Try to extract JSON from the response
        try:
            # Find JSON array in the response
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            rec = SongRecommendation(
                                title=item.get("title", "Unknown"),
                                artist=item.get("artist", "Unknown"),
                                reason=item.get("reason"),
                                genre=item.get("genre"),
                                mood=item.get("mood")
                            )
                            recommendations.append(rec)
        except json.JSONDecodeError:
            # Fallback: try to parse line by line
            recommendations = self._parse_text_format(content)
        
        return recommendations
    
    def _parse_text_format(self, content: str) -> List[SongRecommendation]:
        """
        Fallback parser for non-JSON responses.
        
        Attempts to extract song titles and artists from text format.
        """
        recommendations = []
        lines = content.strip().split('\n')
        
        current_song = {}
        for line in lines:
            line = line.strip()
            if not line:
                if current_song.get("title") and current_song.get("artist"):
                    recommendations.append(SongRecommendation(**current_song))
                    current_song = {}
                continue
            
            # Try to match patterns like "1. Song Title - Artist"
            match = re.match(r'^\d+\.\s*["\']?(.+?)["\']?\s*[-–—by]+\s*(.+?)$', line, re.IGNORECASE)
            if match:
                title = match.group(1).strip().strip('"\'')
                artist = match.group(2).strip().strip('"\'')
                recommendations.append(SongRecommendation(title=title, artist=artist))
                continue
            
            # Try patterns like "Title: Song Name"
            if line.lower().startswith("title:"):
                current_song["title"] = line[6:].strip().strip('"\'')
            elif line.lower().startswith("artist:"):
                current_song["artist"] = line[7:].strip().strip('"\'')
            elif line.lower().startswith("reason:"):
                current_song["reason"] = line[7:].strip()
            elif line.lower().startswith("genre:"):
                current_song["genre"] = line[6:].strip()
            elif line.lower().startswith("mood:"):
                current_song["mood"] = line[5:].strip()
        
        # Don't forget the last song
        if current_song.get("title") and current_song.get("artist"):
            recommendations.append(SongRecommendation(**current_song))
        
        return recommendations
    
    async def check_health(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            # List available models
            models = await self.client.list()
            model_names = [m.get("name", "").split(":")[0] for m in models.get("models", [])]
            return self.model in model_names or f"{self.model}:latest" in [m.get("name", "") for m in models.get("models", [])]
        except Exception:
            return False
    
    def flush_langfuse(self):
        """Flush pending Langfuse events. Call before shutdown."""
        if self.langfuse:
            try:
                self.langfuse.flush()
                logger.info("Langfuse events flushed")
            except Exception as e:
                logger.warning(f"Error flushing Langfuse: {e}")
    
    def shutdown(self):
        """Shutdown the client and flush Langfuse."""
        self.flush_langfuse()
        if self.langfuse:
            try:
                self.langfuse.shutdown()
            except Exception:
                pass
    
    async def extract_search_queries(
        self, 
        user_text: str,
        trace_metadata: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ) -> List[str]:
        """
        Extract YouTube Music search queries from user's mood description.
        
        Instead of generating song names, this method interprets the user's
        request and generates effective search queries for YouTube Music.
        
        Args:
            user_text: User's mood/vibe description
            trace_metadata: Optional metadata for Langfuse tracing
            system_prompt: Optional custom system prompt (e.g., with user preferences)
            
        Returns:
            List of search queries to use with YouTube Music
        """
        # Use custom system prompt if provided, otherwise use default
        if system_prompt:
            # Append query generation instructions to custom prompt
            final_system_prompt = f"""{system_prompt}

ADDITIONAL INSTRUCTIONS FOR SEARCH QUERIES:
You must also generate YouTube Music search queries based on the user's request.

QUERY RULES:
1. Output ONLY search queries, one per line
2. Generate exactly 6-8 queries
3. NO commentary, NO disclaimers, NO notes, NO explanations
4. Use the EXACT terms the user provides - do not sanitize or soften them
5. Consider the user's preferences when generating queries

QUERY STYLE:
- Genre + mood: "sensual R&B", "alternative rock 2020s"
- Artist vibes: "songs like [artist]", "music similar to [song]"
- Playlists: "chill evening playlist", "workout motivation songs"
"""
        else:
            final_system_prompt = """You are a music search query generator for a music recommendation app.

TASK: Convert the user's request into YouTube Music search queries.

ABSOLUTE RULES - FOLLOW EXACTLY:
1. Output ONLY search queries, one per line
2. Generate exactly 6-8 queries
3. NO commentary, NO disclaimers, NO notes, NO explanations
4. NO "Please note", NO "I'll adjust", NO warnings of any kind
5. Use the EXACT terms the user provides - do not sanitize or soften them
6. If user says "erotic" → use "erotic". If user says "sexy" → use "sexy"

QUERY STYLE:
- Genre + mood: "sensual R&B", "erotic slow jams", "sexy bedroom music"
- Playlists: "songs for intimacy", "late night bedroom playlist"
- Artist vibes: "songs like The Weeknd", "music like Marvin Gaye"

WRONG OUTPUT (never do this):
"Please note that... I'll adjust the request..."
"Here are some family-friendly alternatives..."

CORRECT OUTPUT (always do this):
erotic R&B songs
sexy slow jams playlist
sensual bedroom music
[more queries...]"""

        user_prompt = f"""Convert this music request into YouTube Music search queries:

"{user_text}"

Generate 5-8 search queries that will find music matching this description:"""

        # Start Langfuse trace if available (v2 API)
        trace = None
        generation = None
        if self.langfuse:
            try:
                trace = self.langfuse.trace(
                    name="extract_search_queries",
                    input={"user_text": user_text, "has_custom_prompt": system_prompt is not None},
                    metadata=trace_metadata or {}
                )
                generation = trace.generation(
                    name="ollama_query_extraction",
                    model=self.model,
                    input={
                        "messages": [
                            {"role": "system", "content": final_system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    },
                    model_parameters={"temperature": 0.7}
                )
            except Exception as e:
                logger.warning(f"Langfuse trace error: {e}")

        try:
            response = await self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": final_system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                options={"temperature": 0.7}
            )
            
            response_text = response.get("message", {}).get("content", "")
            
            # Parse queries (one per line)
            queries = []
            for line in response_text.strip().split("\n"):
                line = line.strip()
                if not line or len(line) < 3:
                    continue
                    
                # Remove numbering patterns: "1.", "1)", "1:", "-", "*", "•"
                line = re.sub(r'^[\d]+[.):]\s*', '', line)
                line = re.sub(r'^[-*•]\s*', '', line)
                
                # Remove "query X:" prefix (case insensitive)
                line = re.sub(r'^query\s*\d*[:\s]*', '', line, flags=re.IGNORECASE)
                
                # Remove surrounding quotes
                line = line.strip('"\'')
                line = line.strip()
                
                if line and len(line) > 3:
                    queries.append(line)
            
            result = queries[:8] if queries else [user_text]
            
            # End Langfuse generation
            if generation:
                try:
                    generation.end(
                        output=response_text,
                        usage={
                            "prompt_tokens": response.get("prompt_eval_count", 0),
                            "completion_tokens": response.get("eval_count", 0)
                        },
                        metadata={
                            "queries": result,
                            "count": len(result),
                            "success": True
                        }
                    )
                except Exception as e:
                    logger.warning(f"Langfuse generation end error: {e}")
            
            return result
            
        except Exception as e:
            # End Langfuse generation with error
            if generation:
                try:
                    generation.end(
                        output=str(e),
                        level="ERROR",
                        metadata={"success": False}
                    )
                except Exception:
                    pass
            
            logger.error(f"Error extracting search queries: {e}")
            return [user_text]  # Fallback to original text


# System prompt templates
class PromptTemplates:
    """Templates for system prompts based on user type."""
    
    @staticmethod
    def registered_user_prompt(
        preferences_summary: Dict[str, Any],
        dislikes: List[str]
    ) -> str:
        """
        Build system prompt for registered users with known preferences.
        
        Args:
            preferences_summary: Summary of user's music preferences
            dislikes: List of disliked songs/artists
        """
        favorite_genres = preferences_summary.get("favorite_genres", [])
        favorite_artists = preferences_summary.get("favorite_artists", [])
        recent_likes = preferences_summary.get("recent_likes", [])
        disliked_artists = preferences_summary.get("disliked_artists", [])
        
        prompt = """You are an expert music curator and recommendation engine. 
You have deep knowledge of music across ALL genres, eras, and cultures worldwide.

CRITICAL: ALWAYS recommend music that DIRECTLY matches the user's request.
- If they ask for "sexy music" → recommend sensual R&B, slow jams, romantic songs
- If they ask for "party music" → recommend dance, pop, electronic hits
- If they ask for "sad songs" → recommend emotional ballads, melancholic tracks
- If they mention a specific genre, artist, or mood → stick to that exactly
- Do NOT substitute with unrelated genres (e.g., don't recommend video game music for "sexy")

CONTEXT ABOUT THIS USER:
"""
        
        if favorite_genres:
            prompt += f"\n- Favorite genres: {', '.join(favorite_genres)}"
        
        if favorite_artists:
            prompt += f"\n- Favorite artists: {', '.join(favorite_artists[:10])}"
        
        if recent_likes:
            prompt += f"\n- Recently liked songs: {', '.join(recent_likes[:5])}"
        
        if dislikes:
            prompt += f"\n- Specific songs to NEVER recommend (user disliked these exact songs): {', '.join(dislikes[:15])}"
        
        prompt += """

DISLIKE HANDLING - IMPORTANT:
1. NEVER recommend the EXACT songs from the dislike list
2. Disliking a song does NOT mean the user dislikes the artist - other songs by the same artist are OK
3. Only block the specific song that was disliked, not similar songs or the artist's catalog
4. The dislike list is for exact song blocking, not style/genre filtering

SORTING ORDER:
1. Start with the MOST POPULAR and WELL-KNOWN tracks that match the request
2. Then include lesser-known gems and deeper cuts
3. Consider streaming popularity and cultural impact

INSTRUCTIONS:
1. ALWAYS prioritize the user's current request over their history
2. If user asks for "sexy music" → recommend sensual songs, NOT video game music
3. Use preference data to personalize, but don't override the current request
4. NEVER recommend the exact songs from the dislike list
5. Other songs by the same artist ARE allowed
6. Start with popular tracks, then add hidden gems
"""
        
        return prompt
    
    @staticmethod
    def guest_user_prompt() -> str:
        """Build system prompt for guest users (no history)."""
        return """You are an expert music curator and recommendation engine.
You have deep knowledge of music across ALL genres, eras, and cultures worldwide.

CONTEXT: This is a GUEST USER with no preference history.

CRITICAL: ALWAYS recommend music that DIRECTLY matches the user's request.
- If they ask for "sexy music" → recommend sensual R&B, slow jams, romantic songs (Marvin Gaye, The Weeknd, etc.)
- If they ask for "party music" → recommend dance, pop, electronic hits
- If they ask for "sad songs" → recommend emotional ballads, melancholic tracks
- If they ask for "rock" → recommend rock music
- If they mention a specific artist, genre, or mood → stick to that EXACTLY
- Do NOT substitute with unrelated genres

SPECIAL CASES:
- If they mention a VIDEO GAME, MOVIE, or ANIME → recommend music FROM that franchise
- If they mention a specific composer → recommend works by that composer

SORTING ORDER:
1. Start with the MOST POPULAR and WELL-KNOWN tracks that match the request
2. Then include lesser-known gems and deeper cuts
3. Consider streaming popularity and cultural impact

GENERAL INSTRUCTIONS:
1. Base recommendations purely on the current input (mood or song)
2. Provide diverse recommendations within the requested genre/mood
3. Do NOT bias toward any specific genre unless the user asks for it
4. Aim for variety to help discover what they might like
"""
    
    @staticmethod
    def build_user_prompt_from_mood(mood: str) -> str:
        """Build user prompt for mood-based recommendations."""
        return f"""I'm looking for music that matches this description:

"{mood}"

CRITICAL MATCHING RULES:
1. Match my request LITERALLY - if I ask for "sexy music", recommend sensual songs (R&B, slow jams, etc.)
2. If I ask for "party music", recommend dance/pop/electronic hits
3. If I ask for "rock", recommend rock music
4. If I ask for "sad songs", recommend melancholic tracks
5. ONLY recommend video game/anime music if I EXPLICITLY mention a game, anime, or soundtrack
6. Do NOT default to video game music for generic mood requests

SORTING: Most popular/well-known tracks FIRST, then lesser-known gems.

Please recommend songs that DIRECTLY match my request."""
    
    @staticmethod
    def build_user_prompt_from_song(
        title: str,
        artist: str,
        genre: Optional[str] = None,
        additional_context: str = ""
    ) -> str:
        """Build user prompt for song-based recommendations."""
        prompt = f"""I want recommendations based on this song:

Song: "{title}"
Artist: {artist}"""
        
        if genre:
            prompt += f"\nGenre: {genre}"
        
        prompt += """

STEP 1 - First, analyze this song and identify its characteristics:
- Primary mood/vibe (e.g., sensual, melancholic, energetic, romantic, chill, dark, uplifting)
- Tempo feel (slow/ballad, mid-tempo, upbeat/fast)
- Musical style and subgenres
- Typical use cases (e.g., romantic evening, workout, relaxation, party)

STEP 2 - Based on your analysis, recommend songs that match the SAME MOOD and VIBE.
- Prioritize songs with similar emotional feel and atmosphere
- Include both well-known tracks and hidden gems
- Mix artists from the same genre and adjacent genres

The recommendations should make someone who loves this song feel the same emotions."""
        
        if additional_context:
            prompt += f"\n\nAdditional user preference: {additional_context}"
        
        return prompt
    
    @staticmethod
    def build_combined_prompt(
        mood: str,
        title: str,
        artist: str,
        genre: Optional[str] = None
    ) -> str:
        """Build user prompt combining both mood description and song reference."""
        prompt = f"""I'm looking for music recommendations based on TWO inputs:

1. MY CURRENT MOOD/VIBE:
"{mood}"

2. A SONG I LIKE:
Song: "{title}"
Artist: {artist}"""
        
        if genre:
            prompt += f"\nGenre: {genre}"
        
        prompt += """

Please recommend songs that COMBINE both aspects:
- Capture the mood and feeling I described
- Share musical characteristics with the reference song
- Consider the intersection of the emotional tone and the musical style

The ideal recommendations should feel like they belong in a playlist that bridges 
my current mood with the sonic qualities of the reference track."""
        
        return prompt
    
    @staticmethod
    def build_continuation_prompt(previous_songs: List[str]) -> str:
        """
        Build prompt addition for "Load 10 more" functionality.
        
        Tells the LLM to avoid previously recommended songs.
        """
        return f"""
IMPORTANT: The following songs have already been recommended. 
DO NOT include any of these in your new recommendations:
{chr(10).join(f'- {song}' for song in previous_songs)}

Provide 10 NEW and DIFFERENT recommendations."""


# Singleton instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get the Ollama client singleton."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
