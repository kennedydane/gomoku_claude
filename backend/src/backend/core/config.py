"""
Configuration settings for the Gomoku backend application.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application settings
    app_name: str = "Gomoku Game API"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Server settings
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    # Database settings
    database_url: str = Field(
        default="postgresql+asyncpg://gomoku_user:gomoku_password@localhost:5432/gomoku_db",
        description="Database connection URL"
    )
    database_echo: bool = Field(default=False, description="Enable SQLAlchemy query logging")
    
    # CORS settings
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )
    allowed_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed CORS methods"
    )
    allowed_headers: list[str] = Field(
        default=["*"],
        description="Allowed CORS headers"
    )
    
    # Security settings
    secret_key: str = Field(
        default="your-secret-key-change-this-in-production",
        description="Secret key for cryptographic signing"
    )
    
    # Logging settings  
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="Loguru log format"
    )
    
    # Game settings
    default_board_size: int = Field(default=15, description="Default board size (15x15)")
    max_games_per_user: int = Field(default=10, description="Maximum concurrent games per user")
    game_timeout_minutes: int = Field(default=30, description="Game timeout in minutes")
    
    # Rate limiting
    requests_per_minute: int = Field(default=60, description="API requests per minute per IP")
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic migrations."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Global settings instance
settings = get_settings()