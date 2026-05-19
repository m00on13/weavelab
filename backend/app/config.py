"""
Application settings loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Global configuration — values can be overridden via .env or env vars."""

    # CORS
    cors_origins: list[str] = Field(default=["*"])

    # Image processing
    max_image_size_mb: int = Field(default=10)
    default_downscale_factor: int = Field(default=4)

    # Generation defaults
    default_num_nails: int = Field(default=300)
    default_max_connections: int = Field(default=10000)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
