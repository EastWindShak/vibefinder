"""
Audio Analysis Service using CLAP model.

Extracts mood, genre, and other characteristics from audio files
that couldn't be identified by Shazam.
"""

import logging
import io
import numpy as np
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy load heavy dependencies
_clap_model = None
_clap_processor = None


@dataclass
class AudioAnalysisResult:
    """Result of audio analysis."""
    mood_tags: List[str]  # e.g., ["sensual", "melancholic", "relaxing"]
    genre_tags: List[str]  # e.g., ["R&B", "soul", "jazz"]
    tempo_description: str  # e.g., "slow", "moderate", "fast"
    energy_level: str  # e.g., "low", "medium", "high"
    confidence_scores: Dict[str, float]  # tag -> confidence
    
    def to_search_keywords(self) -> List[str]:
        """Convert analysis to search-friendly keywords."""
        keywords = []
        
        # Combine mood and genre for effective searches
        for mood in self.mood_tags[:3]:
            keywords.append(mood)
            for genre in self.genre_tags[:2]:
                keywords.append(f"{mood} {genre}")
        
        # Add tempo-based keywords
        if self.tempo_description == "slow":
            keywords.extend(["slow jams", "ballads"])
        elif self.tempo_description == "fast":
            keywords.extend(["upbeat", "energetic"])
        
        return keywords


# Predefined labels for CLAP classification
MOOD_LABELS = [
    "happy", "sad", "melancholic", "romantic", "sensual", "relaxing",
    "energetic", "aggressive", "peaceful", "nostalgic", "hopeful",
    "dark", "uplifting", "dreamy", "intense", "chill", "groovy",
    "emotional", "passionate", "mysterious"
]

GENRE_LABELS = [
    "pop", "rock", "hip-hop", "R&B", "soul", "jazz", "classical",
    "electronic", "dance", "country", "folk", "blues", "metal",
    "punk", "reggae", "latin", "indie", "alternative", "ambient",
    "funk", "disco"
]

TEMPO_LABELS = [
    "very slow ballad",
    "slow tempo",
    "moderate tempo", 
    "upbeat fast tempo",
    "very fast energetic"
]

ENERGY_LABELS = [
    "very calm and quiet",
    "low energy relaxed",
    "moderate energy",
    "high energy",
    "very high energy intense"
]


def _load_clap_model():
    """Lazy load the CLAP model."""
    global _clap_model, _clap_processor
    
    if _clap_model is not None:
        return _clap_model, _clap_processor
    
    if not settings.ENABLE_AUDIO_ANALYSIS:
        logger.info("Audio analysis is disabled")
        return None, None
    
    try:
        from transformers import ClapModel, ClapProcessor
        
        model_name = settings.AUDIO_ANALYSIS_MODEL
        logger.info(f"Loading CLAP model: {model_name}")
        
        _clap_processor = ClapProcessor.from_pretrained(model_name)
        _clap_model = ClapModel.from_pretrained(model_name)
        
        logger.info("CLAP model loaded successfully")
        return _clap_model, _clap_processor
        
    except ImportError:
        logger.warning("transformers not installed - audio analysis disabled")
        return None, None
    except Exception as e:
        logger.error(f"Failed to load CLAP model: {e}")
        return None, None


def _load_audio_from_bytes(audio_bytes: bytes, target_sr: int = 48000) -> Optional[np.ndarray]:
    """Load audio from bytes and convert to numpy array."""
    try:
        import librosa
        import soundfile as sf
        
        # Try to load with soundfile first (faster)
        try:
            audio_file = io.BytesIO(audio_bytes)
            audio, sr = sf.read(audio_file)
            
            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            
            # Resample if needed
            if sr != target_sr:
                audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
            
            return audio.astype(np.float32)
            
        except Exception:
            # Fallback to librosa (handles more formats)
            audio_file = io.BytesIO(audio_bytes)
            audio, sr = librosa.load(audio_file, sr=target_sr, mono=True)
            return audio.astype(np.float32)
            
    except ImportError:
        logger.warning("librosa/soundfile not installed - cannot process audio")
        return None
    except Exception as e:
        logger.error(f"Failed to load audio: {e}")
        return None


def _classify_audio(
    audio: np.ndarray,
    labels: List[str],
    model,
    processor,
    top_k: int = 3
) -> List[tuple]:
    """Classify audio against a list of text labels."""
    try:
        import torch
        
        # Prepare inputs
        inputs = processor(
            text=labels,
            audios=[audio],
            return_tensors="pt",
            padding=True,
            sampling_rate=48000
        )
        
        with torch.no_grad():
            outputs = model(**inputs)
            
            # Get similarity scores
            logits_per_audio = outputs.logits_per_audio
            probs = torch.softmax(logits_per_audio, dim=-1)
            
            # Get top-k predictions
            top_probs, top_indices = torch.topk(probs[0], min(top_k, len(labels)))
            
            results = [
                (labels[idx], prob.item())
                for idx, prob in zip(top_indices, top_probs)
            ]
            
            return results
            
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return []


async def analyze_audio(audio_bytes: bytes) -> Optional[AudioAnalysisResult]:
    """
    Analyze audio to extract mood, genre, and other characteristics.
    
    Args:
        audio_bytes: Raw audio data
        
    Returns:
        AudioAnalysisResult with extracted characteristics, or None if analysis fails
    """
    model, processor = _load_clap_model()
    
    if model is None or processor is None:
        logger.warning("CLAP model not available")
        return None
    
    # Load audio
    audio = _load_audio_from_bytes(audio_bytes)
    if audio is None:
        return None
    
    # Limit audio length (CLAP works best with ~10-30 seconds)
    max_samples = 48000 * 30  # 30 seconds
    if len(audio) > max_samples:
        # Take middle section
        start = (len(audio) - max_samples) // 2
        audio = audio[start:start + max_samples]
    
    try:
        # Classify mood
        mood_results = _classify_audio(audio, MOOD_LABELS, model, processor, top_k=5)
        mood_tags = [tag for tag, _ in mood_results if _ > 0.1]  # Filter low confidence
        
        # Classify genre
        genre_results = _classify_audio(audio, GENRE_LABELS, model, processor, top_k=4)
        genre_tags = [tag for tag, _ in genre_results if _ > 0.1]
        
        # Classify tempo
        tempo_results = _classify_audio(audio, TEMPO_LABELS, model, processor, top_k=1)
        tempo_map = {
            "very slow ballad": "slow",
            "slow tempo": "slow",
            "moderate tempo": "moderate",
            "upbeat fast tempo": "fast",
            "very fast energetic": "fast"
        }
        tempo_description = tempo_map.get(tempo_results[0][0], "moderate") if tempo_results else "moderate"
        
        # Classify energy
        energy_results = _classify_audio(audio, ENERGY_LABELS, model, processor, top_k=1)
        energy_map = {
            "very calm and quiet": "low",
            "low energy relaxed": "low",
            "moderate energy": "medium",
            "high energy": "high",
            "very high energy intense": "high"
        }
        energy_level = energy_map.get(energy_results[0][0], "medium") if energy_results else "medium"
        
        # Build confidence scores
        confidence_scores = {}
        for tag, score in mood_results + genre_results:
            confidence_scores[tag] = score
        
        return AudioAnalysisResult(
            mood_tags=mood_tags,
            genre_tags=genre_tags,
            tempo_description=tempo_description,
            energy_level=energy_level,
            confidence_scores=confidence_scores
        )
        
    except Exception as e:
        logger.error(f"Audio analysis failed: {e}")
        return None


async def get_search_queries_from_audio(audio_bytes: bytes) -> List[str]:
    """
    Analyze audio and return search queries for YouTube Music.
    
    This is a convenience function that combines analysis with query generation.
    
    Args:
        audio_bytes: Raw audio data
        
    Returns:
        List of search query strings
    """
    result = await analyze_audio(audio_bytes)
    
    if result is None:
        return []
    
    queries = []
    
    # Build queries from mood + genre combinations
    for mood in result.mood_tags[:3]:
        queries.append(f"{mood} music")
        for genre in result.genre_tags[:2]:
            queries.append(f"{mood} {genre}")
    
    # Add genre-only queries
    for genre in result.genre_tags[:2]:
        queries.append(f"{genre} songs")
    
    # Add tempo/energy-based queries
    if result.tempo_description == "slow" and result.energy_level == "low":
        queries.append("slow relaxing music")
        queries.append("chill ballads")
    elif result.tempo_description == "fast" and result.energy_level == "high":
        queries.append("upbeat energetic music")
        queries.append("party songs")
    
    return queries[:8]  # Limit to 8 queries


# Lightweight alternative: Simple audio feature extraction without CLAP
async def analyze_audio_simple(audio_bytes: bytes) -> Optional[Dict[str, Any]]:
    """
    Simple audio analysis using librosa (no ML model required).
    
    Extracts basic features like tempo, energy, and spectral characteristics.
    Useful as a fallback when CLAP is not available.
    """
    try:
        import librosa
        import numpy as np
        
        # Load audio
        audio = _load_audio_from_bytes(audio_bytes, target_sr=22050)
        if audio is None:
            return None
        
        # Extract tempo
        tempo, _ = librosa.beat.beat_track(y=audio, sr=22050)
        
        # Extract RMS energy
        rms = librosa.feature.rms(y=audio)[0]
        avg_energy = np.mean(rms)
        
        # Classify tempo
        if tempo < 80:
            tempo_desc = "slow"
        elif tempo < 120:
            tempo_desc = "moderate"
        else:
            tempo_desc = "fast"
        
        # Classify energy
        if avg_energy < 0.05:
            energy_desc = "low"
        elif avg_energy < 0.15:
            energy_desc = "medium"
        else:
            energy_desc = "high"
        
        return {
            "tempo_bpm": float(tempo),
            "tempo_description": tempo_desc,
            "energy_level": energy_desc,
            "avg_energy": float(avg_energy)
        }
        
    except ImportError:
        logger.warning("librosa not installed")
        return None
    except Exception as e:
        logger.error(f"Simple audio analysis failed: {e}")
        return None
