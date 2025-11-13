from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }
    
    # Telegram Bot Configuration
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    
    # API Configuration
    coingecko_base_url: str = Field(
        default="https://api.coingecko.com/api/v3", 
        alias="COINGECKO_BASE_URL"
    )
    api_timeout: int = Field(default=30, alias="API_TIMEOUT")
    api_max_retries: int = Field(default=3, alias="API_MAX_RETRIES")
    api_retry_delay: float = Field(default=1.0, alias="API_RETRY_DELAY")
    
    # Scheduler Configuration
    scheduler_timezone: str = Field(default="UTC", alias="SCHEDULER_TIMEZONE")
    scheduler_max_workers: int = Field(default=3, alias="SCHEDULER_MAX_WORKERS")
    
    # Optional Proxy Configuration
    proxy_url: Optional[str] = Field(None, alias="PROXY_URL")
    proxy_username: Optional[str] = Field(None, alias="PROXY_USERNAME")
    proxy_password: Optional[str] = Field(None, alias="PROXY_PASSWORD")
    
    # Database Configuration
    database_url: str = Field(..., alias="DATABASE_URL")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


# Global settings instance
settings = Settings()