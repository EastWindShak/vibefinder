"""
ChromaDB client for storing and retrieving user music preferences.

This module handles vector storage for registered users' music tastes,
enabling semantic search and preference-based filtering.

Uses intfloat/multilingual-e5-large for embeddings - a high-quality
multilingual embedding model optimized for semantic search.
"""
import uuid
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import chromadb
from chromadb.utils import embedding_functions

from app.core.config import settings

logger = logging.getLogger(__name__)

# E5 embedding model configuration
# multilingual-e5-large supports 100+ languages and has 1024 dimensions
E5_MODEL_NAME = "intfloat/multilingual-e5-large"


@dataclass
class MusicPreference:
    """Represents a user's music preference entry."""
    song_title: str
    artist: str
    genre: Optional[str] = None
    mood_tags: Optional[List[str]] = None
    feedback_score: int = 1  # 1 for like, -1 for dislike
    youtube_video_id: Optional[str] = None
    
    def to_document(self) -> str:
        """Convert preference to a document string for embedding."""
        parts = [f"Song: {self.song_title}", f"Artist: {self.artist}"]
        if self.genre:
            parts.append(f"Genre: {self.genre}")
        if self.mood_tags:
            parts.append(f"Mood: {', '.join(self.mood_tags)}")
        return " | ".join(parts)
    
    def to_metadata(self) -> Dict[str, Any]:
        """Convert preference to metadata dict."""
        return {
            "song_title": self.song_title,
            "artist": self.artist,
            "genre": self.genre or "",
            "mood_tags": ",".join(self.mood_tags) if self.mood_tags else "",
            "feedback_score": self.feedback_score,
            "youtube_video_id": self.youtube_video_id or ""
        }


class E5EmbeddingFunction(embedding_functions.EmbeddingFunction):
    """
    Custom embedding function for E5 models.
    
    E5 models require specific prefixes for optimal performance:
    - "query: " for search queries
    - "passage: " for documents/passages
    
    This wrapper handles the prefix automatically.
    """
    
    def __init__(self, model_name: str = E5_MODEL_NAME):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model {model_name}: {e}")
            raise
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings for documents (adds 'passage: ' prefix)."""
        # E5 models expect "passage: " prefix for documents
        prefixed_input = [f"passage: {text}" for text in input]
        embeddings = self.model.encode(prefixed_input, normalize_embeddings=True)
        return embeddings.tolist()
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query (adds 'query: ' prefix)."""
        # E5 models expect "query: " prefix for queries
        prefixed_query = f"query: {query}"
        embedding = self.model.encode([prefixed_query], normalize_embeddings=True)
        return embedding[0].tolist()


class ChromaDBClient:
    """
    Client for managing user music preferences in ChromaDB.
    
    Each user has their preferences stored in a dedicated collection,
    separated into 'likes' and 'dislikes' for filtering recommendations.
    
    Uses E5-large multilingual embeddings for high-quality semantic search.
    """
    
    LIKES_COLLECTION_PREFIX = "user_likes_"
    DISLIKES_COLLECTION_PREFIX = "user_dislikes_"
    
    def __init__(self):
        """Initialize ChromaDB client - connects to ChromaDB server via HTTP."""
        # Use HTTP client to connect to ChromaDB server
        self.client = chromadb.HttpClient(
            host=settings.CHROMADB_HOST,
            port=settings.CHROMADB_PORT
        )
        
        # Initialize E5 embedding function
        try:
            self.embedding_function = E5EmbeddingFunction(E5_MODEL_NAME)
            logger.info("ChromaDB client initialized with E5-large embeddings")
        except Exception as e:
            logger.warning(f"Failed to initialize E5 embeddings, using default: {e}")
            self.embedding_function = None
    
    def _get_likes_collection(self, user_id: uuid.UUID) -> chromadb.Collection:
        """Get or create the likes collection for a user."""
        collection_name = f"{self.LIKES_COLLECTION_PREFIX}{str(user_id).replace('-', '_')}"
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"user_id": str(user_id), "type": "likes"},
            embedding_function=self.embedding_function
        )
    
    def _get_dislikes_collection(self, user_id: uuid.UUID) -> chromadb.Collection:
        """Get or create the dislikes collection for a user."""
        collection_name = f"{self.DISLIKES_COLLECTION_PREFIX}{str(user_id).replace('-', '_')}"
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"user_id": str(user_id), "type": "dislikes"},
            embedding_function=self.embedding_function
        )
    
    async def add_preference(
        self, 
        user_id: uuid.UUID, 
        preference: MusicPreference
    ) -> str:
        """
        Add a music preference for a user.
        
        When adding a like, removes the song from dislikes if it exists (and vice versa).
        A song cannot be both liked and disliked at the same time.
        
        Args:
            user_id: The user's UUID
            preference: The music preference to add
            
        Returns:
            The ID of the added preference
        """
        # Choose collection based on feedback score
        if preference.feedback_score > 0:
            collection = self._get_likes_collection(user_id)
            opposite_collection = self._get_dislikes_collection(user_id)
        else:
            collection = self._get_dislikes_collection(user_id)
            opposite_collection = self._get_likes_collection(user_id)
        
        # Remove from opposite collection if exists (like removes dislike, dislike removes like)
        await self._remove_song_from_collection(
            opposite_collection,
            preference.song_title,
            preference.artist,
            preference.youtube_video_id
        )
        
        # Check if already exists in target collection (avoid duplicates)
        existing_id = await self._find_song_in_collection(
            collection,
            preference.song_title,
            preference.artist,
            preference.youtube_video_id
        )
        
        if existing_id:
            # Already exists, return existing ID
            return existing_id
        
        # Generate unique ID for this preference
        pref_id = str(uuid.uuid4())
        
        # Add to collection
        collection.add(
            documents=[preference.to_document()],
            metadatas=[preference.to_metadata()],
            ids=[pref_id]
        )
        
        return pref_id
    
    async def _find_song_in_collection(
        self,
        collection: chromadb.Collection,
        song_title: str,
        artist: str,
        video_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Find a song in a collection by title/artist or video_id.
        
        Returns the document ID if found, None otherwise.
        """
        try:
            results = collection.get(
                limit=500,
                include=["metadatas"]
            )
            
            ids = results.get("ids", [])
            metadatas = results.get("metadatas", [])
            
            title_lower = song_title.lower().strip()
            artist_lower = artist.lower().strip()
            
            for i, metadata in enumerate(metadatas):
                # Check by video_id first (most accurate)
                if video_id and metadata.get("youtube_video_id"):
                    if video_id == metadata.get("youtube_video_id"):
                        return ids[i]
                
                # Check by title + artist
                meta_title = metadata.get("song_title", "").lower().strip()
                meta_artist = metadata.get("artist", "").lower().strip()
                
                if meta_title == title_lower and meta_artist == artist_lower:
                    return ids[i]
            
            return None
        except Exception:
            return None
    
    async def _remove_song_from_collection(
        self,
        collection: chromadb.Collection,
        song_title: str,
        artist: str,
        video_id: Optional[str] = None
    ) -> bool:
        """
        Remove a song from a collection if it exists.
        
        Returns True if a song was removed, False otherwise.
        """
        song_id = await self._find_song_in_collection(
            collection, song_title, artist, video_id
        )
        
        if song_id:
            try:
                collection.delete(ids=[song_id])
                return True
            except Exception:
                return False
        
        return False
    
    async def get_user_preferences(
        self, 
        user_id: uuid.UUID,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get a user's liked music preferences.
        
        Args:
            user_id: The user's UUID
            limit: Maximum number of preferences to return
            
        Returns:
            List of preference dictionaries
        """
        collection = self._get_likes_collection(user_id)
        
        try:
            results = collection.get(
                limit=limit,
                include=["documents", "metadatas"]
            )
            
            preferences = []
            for i, doc in enumerate(results.get("documents", [])):
                metadata = results.get("metadatas", [])[i] if results.get("metadatas") else {}
                preferences.append({
                    "document": doc,
                    "metadata": metadata
                })
            return preferences
        except Exception:
            return []
    
    async def get_user_dislikes(
        self, 
        user_id: uuid.UUID,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get a user's disliked music preferences.
        
        Args:
            user_id: The user's UUID
            limit: Maximum number of dislikes to return
            
        Returns:
            List of dislike dictionaries
        """
        collection = self._get_dislikes_collection(user_id)
        
        try:
            results = collection.get(
                limit=limit,
                include=["documents", "metadatas"]
            )
            
            dislikes = []
            for i, doc in enumerate(results.get("documents", [])):
                metadata = results.get("metadatas", [])[i] if results.get("metadatas") else {}
                dislikes.append({
                    "document": doc,
                    "metadata": metadata
                })
            return dislikes
        except Exception:
            return []
    
    async def search_similar_preferences(
        self,
        user_id: uuid.UUID,
        query: str,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for similar music in user's preferences.
        
        Args:
            user_id: The user's UUID
            query: The search query (song description, mood, etc.)
            n_results: Number of results to return
            
        Returns:
            List of similar preferences with distances
        """
        collection = self._get_likes_collection(user_id)
        
        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            similar = []
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            
            for i, doc in enumerate(documents):
                similar.append({
                    "document": doc,
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "distance": distances[i] if i < len(distances) else None
                })
            return similar
        except Exception:
            return []
    
    async def check_if_disliked(
        self,
        user_id: uuid.UUID,
        song_title: str,
        artist: str,
        video_id: Optional[str] = None
    ) -> bool:
        """
        Check if a song is in user's dislikes (strict exact match).
        
        A song is considered disliked if:
        - Same video_id (if provided)
        - OR same title AND artist (case-insensitive)
        
        Args:
            user_id: The user's UUID
            song_title: The song title to check
            artist: The artist name
            video_id: Optional YouTube video ID for exact matching
            
        Returns:
            True if the song is disliked, False otherwise
        """
        dislikes = await self.get_user_dislikes(user_id, limit=500)
        
        # Normalize for comparison
        title_lower = song_title.lower().strip()
        artist_lower = artist.lower().strip()
        
        for dislike in dislikes:
            metadata = dislike.get("metadata", {})
            
            # Check by video_id first (most accurate)
            if video_id and metadata.get("youtube_video_id"):
                if video_id == metadata.get("youtube_video_id"):
                    return True
            
            # Check by title + artist (case-insensitive, stripped)
            dislike_title = metadata.get("song_title", "").lower().strip()
            dislike_artist = metadata.get("artist", "").lower().strip()
            
            if dislike_title == title_lower and dislike_artist == artist_lower:
                return True
        
        return False
    
    async def get_dislike_similarity_scores(
        self,
        user_id: uuid.UUID,
        songs: List[Dict[str, str]]
    ) -> List[float]:
        """
        Get similarity scores for songs against user's dislikes.
        
        Returns a penalty score (0.0 to 1.0) for each song:
        - 0.0 = no similarity to dislikes (best)
        - 1.0 = very similar to dislikes (worst)
        
        This is used to deprioritize (not block) similar songs.
        
        Args:
            user_id: The user's UUID
            songs: List of dicts with 'title' and 'artist' keys
            
        Returns:
            List of penalty scores (same order as input songs)
        """
        collection = self._get_dislikes_collection(user_id)
        penalty_scores = []
        
        try:
            # Check if user has any dislikes
            count = collection.count()
            if count == 0:
                return [0.0] * len(songs)
            
            for song in songs:
                title = song.get("title", "")
                artist = song.get("artist", "")
                query = f"Song: {title} | Artist: {artist}"
                
                try:
                    results = collection.query(
                        query_texts=[query],
                        n_results=3,  # Check top 3 similar dislikes
                        include=["metadatas", "distances"]
                    )
                    
                    distances = results.get("distances", [[]])[0]
                    metadatas = results.get("metadatas", [[]])[0]
                    
                    if not distances:
                        penalty_scores.append(0.0)
                        continue
                    
                    # Calculate penalty based on similarity to dislikes
                    # Lower distance = more similar = higher penalty
                    min_distance = min(distances) if distances else 1.0
                    
                    # NOTE: We do NOT penalize same artist - only the exact song is blocked
                    # This allows other songs from the same artist to be recommended
                    
                    # Convert distance to penalty (inverse relationship)
                    # ChromaDB L2 distances typically range 0-2 for similar items
                    # Only apply penalty for VERY similar songs (same title different version, etc.)
                    if min_distance < 0.15:
                        # Extremely similar (likely same song, different version) - high penalty
                        base_penalty = 0.7
                    elif min_distance < 0.3:
                        # Very similar song - medium penalty
                        base_penalty = 0.4
                    elif min_distance < 0.5:
                        # Somewhat similar - low penalty
                        base_penalty = 0.15
                    else:
                        # Not very similar - no penalty
                        base_penalty = 0.0
                    
                    penalty_scores.append(base_penalty)
                    
                except Exception:
                    penalty_scores.append(0.0)
            
            return penalty_scores
            
        except Exception:
            return [0.0] * len(songs)
    
    async def get_all_disliked_songs(
        self,
        user_id: uuid.UUID
    ) -> List[Dict[str, str]]:
        """
        Get all disliked songs for a user (for strict filtering).
        
        Returns:
            List of dicts with song_title, artist, and video_id
        """
        dislikes = await self.get_user_dislikes(user_id, limit=500)
        
        return [
            {
                "title": d.get("metadata", {}).get("song_title", ""),
                "artist": d.get("metadata", {}).get("artist", ""),
                "video_id": d.get("metadata", {}).get("youtube_video_id", "")
            }
            for d in dislikes
        ]
    
    async def get_user_preferences_with_ids(
        self,
        user_id: uuid.UUID,
        preference_type: str = "likes",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get user preferences with their ChromaDB IDs for deletion.
        
        Args:
            user_id: The user's UUID
            preference_type: "likes" or "dislikes"
            limit: Maximum number of preferences to return
            
        Returns:
            List of preference dictionaries with IDs
        """
        if preference_type == "likes":
            collection = self._get_likes_collection(user_id)
        else:
            collection = self._get_dislikes_collection(user_id)
        
        try:
            results = collection.get(
                limit=limit,
                include=["documents", "metadatas"]
            )
            
            preferences = []
            ids = results.get("ids", [])
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            
            for i, doc_id in enumerate(ids):
                metadata = metadatas[i] if i < len(metadatas) else {}
                preferences.append({
                    "id": doc_id,
                    "song_title": metadata.get("song_title", ""),
                    "artist": metadata.get("artist", ""),
                    "genre": metadata.get("genre", ""),
                    "video_id": metadata.get("youtube_video_id", ""),
                    "mood_tags": metadata.get("mood_tags", "").split(",") if metadata.get("mood_tags") else []
                })
            return preferences
        except Exception:
            return []
    
    async def delete_preference(
        self,
        user_id: uuid.UUID,
        preference_id: str,
        preference_type: str = "likes"
    ) -> bool:
        """
        Delete a specific preference by ID.
        
        Args:
            user_id: The user's UUID
            preference_id: The ChromaDB document ID
            preference_type: "likes" or "dislikes"
            
        Returns:
            True if deletion was successful
        """
        if preference_type == "likes":
            collection = self._get_likes_collection(user_id)
        else:
            collection = self._get_dislikes_collection(user_id)
        
        try:
            collection.delete(ids=[preference_id])
            return True
        except Exception:
            return False
    
    async def get_preferences_counts(
        self,
        user_id: uuid.UUID
    ) -> Dict[str, int]:
        """
        Get counts of likes and dislikes for a user.
        
        Returns:
            Dict with 'likes' and 'dislikes' counts
        """
        try:
            likes_collection = self._get_likes_collection(user_id)
            dislikes_collection = self._get_dislikes_collection(user_id)
            
            return {
                "likes": likes_collection.count(),
                "dislikes": dislikes_collection.count()
            }
        except Exception:
            return {"likes": 0, "dislikes": 0}
    
    async def get_preference_summary(
        self,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get a summary of user's music preferences for prompt injection.
        
        Returns a structured summary suitable for including in LLM prompts.
        """
        likes = await self.get_user_preferences(user_id, limit=30)
        dislikes = await self.get_user_dislikes(user_id, limit=30)
        
        # Extract genres and artists
        liked_genres = set()
        liked_artists = set()
        disliked_artists = set()
        
        for pref in likes:
            metadata = pref.get("metadata", {})
            if metadata.get("genre"):
                liked_genres.add(metadata["genre"])
            if metadata.get("artist"):
                liked_artists.add(metadata["artist"])
        
        for pref in dislikes:
            metadata = pref.get("metadata", {})
            if metadata.get("artist"):
                disliked_artists.add(metadata["artist"])
        
        return {
            "total_likes": len(likes),
            "total_dislikes": len(dislikes),
            "favorite_genres": list(liked_genres)[:10],
            "favorite_artists": list(liked_artists)[:15],
            "disliked_artists": list(disliked_artists)[:10],
            "recent_likes": [
                f"{p.get('metadata', {}).get('song_title', 'Unknown')} - {p.get('metadata', {}).get('artist', 'Unknown')}"
                for p in likes[:10]
            ]
        }
    
    async def delete_user_data(self, user_id: uuid.UUID) -> bool:
        """
        Delete all preference data for a user (GDPR compliance).
        
        Args:
            user_id: The user's UUID
            
        Returns:
            True if deletion was successful
        """
        try:
            likes_name = f"{self.LIKES_COLLECTION_PREFIX}{str(user_id).replace('-', '_')}"
            dislikes_name = f"{self.DISLIKES_COLLECTION_PREFIX}{str(user_id).replace('-', '_')}"
            
            try:
                self.client.delete_collection(likes_name)
            except Exception:
                pass
            
            try:
                self.client.delete_collection(dislikes_name)
            except Exception:
                pass
            
            return True
        except Exception:
            return False


# Singleton instance
_chromadb_client: Optional[ChromaDBClient] = None


def get_chromadb_client() -> ChromaDBClient:
    """Get the ChromaDB client singleton."""
    global _chromadb_client
    if _chromadb_client is None:
        _chromadb_client = ChromaDBClient()
    return _chromadb_client
