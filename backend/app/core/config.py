from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "VibeFinder API"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/vibefinder"
    DATABASE_URL_SYNC: str = "postgresql://user:password@localhost:5432/vibefinder"
    
    # ChromaDB
    CHROMADB_HOST: str = "localhost"
    CHROMADB_PORT: int = 8000
    CHROMADB_PERSIST_DIRECTORY: str = "./chroma_data"
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Encryption for OAuth tokens
    OAUTH_ENCRYPTION_KEY: str = "your-fernet-key-here"
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    
    # MCP
    MCP_YTMUSIC_SERVER_PATH: str = "./app/mcp/youtube_music_server.py"
    
    # Last.fm
    LASTFM_API_KEY: str = ""
    
    # Audio Analysis (CLAP model for mood extraction)
    ENABLE_AUDIO_ANALYSIS: bool = True
    AUDIO_ANALYSIS_MODEL: str = "laion/larger_clap_music"
    
    # Langfuse (LLM Observability)
    LANGFUSE_HOST: str = "http://localhost:3000"
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_ENABLED: bool = True
    
    # CORS
    FRONTEND_URL: str = "http://localhost:5173"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
