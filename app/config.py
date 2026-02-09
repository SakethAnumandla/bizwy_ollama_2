from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator
import os

class Settings(BaseSettings):
    # App Info
    PROJECT_NAME: str = "PIMS Enrichment Microservice"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # OpenAI / Ollama
    OPENAI_API_KEY: str = "ollama"
    OPENAI_BASE_URL: Optional[str] = "http://localhost:11434/v1"
    OPENAI_MODEL_NAME: str = "llama3"
    
    # Search
    SEARCH_PROVIDER: Optional[str] = None # None = LLM only, or "duckduckgo", "serpapi", etc.
    SERPAPI_KEY: Optional[str] = None
    BRAVE_API_KEY: Optional[str] = None
    GOOGLE_SEARCH_API_KEY: Optional[str] = None
    GOOGLE_SEARCH_ENGINE_ID: Optional[str] = None
    BING_SEARCH_API_KEY: Optional[str] = None
    
    # Caching
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_DAYS: int = 7
    
    # Security & Rate Limiting
    API_RATE_LIMIT: str = "100/hour"
    CORS_ORIGINS: List[str] = ["*"]
    
    # Processing
    MAX_SEARCH_RESULTS: int = 5
    MAX_TOKENS: int = 4096
    REQUEST_TIMEOUT: int = 120

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"  # Ignore extra environment variables

settings = Settings()
