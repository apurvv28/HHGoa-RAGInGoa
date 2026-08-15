import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Global configuration settings for HH Goa Voice RAG backend."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = Field(default="HH_Goa_Voice_RAG", description="Application Name")
    ENVIRONMENT: str = Field(default="development", description="Environment mode")
    LOG_LEVEL: str = Field(default="INFO", description="Log level")

    # Qdrant Vector DB Settings
    QDRANT_URL: str = Field(default=":memory:", description="Qdrant Cloud URL or :memory: for local testing")
    QDRANT_API_KEY: str = Field(default="", description="Qdrant Cloud API key")
    QDRANT_COLLECTION_NAME: str = Field(default="msmarco_xi_indic", description="Vector collection name")

    # Embedding Model Settings (Indic Multilingual)
    EMBEDDING_MODEL_NAME: str = Field(default="intfloat/multilingual-e5-small", description="Indic embedding model")
    VECTOR_DIMENSION: int = Field(default=384, description="Embedding vector dimension")
    DISTANCE_METRIC: str = Field(default="Cosine", description="Distance metric for vector search")

    # LLM Settings
    GROQ_API_KEY: str = Field(default="", description="Groq API Key")
    GROQ_MODEL: str = Field(default="llama-3.1-8b-instant", description="Fast inference LLM model")

    # Voice API Settings (Strictly Sarvam AI & ElevenLabs)
    SARVAM_API_KEY: str = Field(default="", description="Sarvam AI API key for Indic STT/TTS")
    ELEVENLABS_API_KEY: str = Field(default="", description="ElevenLabs API key for voice synthesis")


settings = Settings()
