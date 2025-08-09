"""Configuration management for Reflex Executive Assistant."""

import os
from typing import List, Optional
from pydantic import BaseSettings, Field, validator
from pydantic_settings import BaseSettings as PydanticBaseSettings


class Settings(PydanticBaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application Configuration
    app_env: str = Field(default="dev", env="APP_ENV")
    port: int = Field(default=8080, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # LLM Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    model_name: str = Field(default="gpt-4o-mini", env="MODEL_NAME")
    model_temperature: float = Field(default=0.1, env="MODEL_TEMPERATURE")
    model_max_tokens: int = Field(default=4000, env="MODEL_MAX_TOKENS")
    
    # Vector Database (Pinecone)
    vector_db_provider: str = Field(default="pinecone", env="VECTOR_DB_PROVIDER")
    pinecone_api_key: str = Field(..., env="PINECONE_API_KEY")
    pinecone_env: str = Field(..., env="PINECONE_ENV")
    pinecone_index: str = Field(..., env="PINECONE_INDEX")
    
    # Database Configuration
    postgres_url: str = Field(..., env="POSTGRES_URL")
    postgres_pool_size: int = Field(default=10, env="POSTGRES_POOL_SIZE")
    postgres_max_overflow: int = Field(default=20, env="POSTGRES_MAX_OVERFLOW")
    
    # Redis Configuration
    redis_url: str = Field(..., env="REDIS_URL")
    redis_pool_size: int = Field(default=10, env="REDIS_POOL_SIZE")
    
    # Google Workspace Integration
    google_client_id: str = Field(..., env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(..., env="GOOGLE_REDIRECT_URI")
    google_service_account_json_base64: Optional[str] = Field(None, env="GOOGLE_SERVICE_ACCOUNT_JSON_BASE64")
    google_application_credentials: Optional[str] = Field(None, env="GOOGLE_APPLICATION_CREDENTIALS")
    
    # Slack Integration
    slack_bot_token: str = Field(..., env="SLACK_BOT_TOKEN")
    slack_signing_secret: str = Field(..., env="SLACK_SIGNING_SECRET")
    slack_app_level_token: str = Field(..., env="SLACK_APP_LEVEL_TOKEN")
    slack_verification_token: str = Field(..., env="SLACK_VERIFICATION_TOKEN")
    
    # Asana Integration
    asana_access_token: str = Field(..., env="ASANA_ACCESS_TOKEN")
    asana_workspace_id: str = Field(..., env="ASANA_WORKSPACE_ID")
    asana_webhook_secret: str = Field(..., env="ASANA_WEBHOOK_SECRET")
    
    # Security and Authentication
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Guardrails and Policy
    excluded_markets: List[str] = Field(default=["therapeutic", "wellness", "medical"], env="EXCLUDED_MARKETS")
    style_no_bold: bool = Field(default=True, env="STYLE_NO_BOLD")
    style_no_emoji: bool = Field(default=True, env="STYLE_NO_EMOJI")
    require_approval: bool = Field(default=True, env="REQUIRE_APPROVAL")
    safe_mode: bool = Field(default=True, env="SAFE_MODE")
    
    # Monitoring and Telemetry
    otel_endpoint: Optional[str] = Field(None, env="OTEL_ENDPOINT")
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    
    # Webhook Configuration
    webhook_base_url: str = Field(..., env="WEBHOOK_BASE_URL")
    slack_webhook_path: str = Field(default="/webhooks/slack/events", env="SLACK_WEBHOOK_PATH")
    gmail_webhook_path: str = Field(default="/webhooks/gmail/notifications", env="GMAIL_WEBHOOK_PATH")
    asana_webhook_path: str = Field(default="/webhooks/asana/events", env="ASANA_WEBHOOK_PATH")
    
    # Email Configuration
    smtp_host: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(..., env="SMTP_USERNAME")
    smtp_password: str = Field(..., env="SMTP_PASSWORD")
    
    # File Storage
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    max_file_size: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    
    # Background Jobs
    celery_broker_url: str = Field(..., env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(..., env="CELERY_RESULT_BACKEND")
    celery_task_serializer: str = Field(default="json", env="CELERY_TASK_SERIALIZER")
    celery_result_serializer: str = Field(default="json", env="CELERY_RESULT_SERIALIZER")
    celery_accept_content: List[str] = Field(default=["json"], env="CELERY_ACCEPT_CONTENT")
    celery_timezone: str = Field(default="UTC", env="CELERY_TIMEZONE")
    celery_enable_utc: bool = Field(default=True, env="CELERY_ENABLE_UTC")
    
    @validator("excluded_markets", pre=True)
    def parse_excluded_markets(cls, v):
        """Parse excluded markets from comma-separated string."""
        if isinstance(v, str):
            return [market.strip() for market in v.split(",")]
        return v
    
    @validator("celery_accept_content", pre=True)
    def parse_celery_accept_content(cls, v):
        """Parse celery accept content from comma-separated string."""
        if isinstance(v, str):
            return [content.strip() for content in v.split(",")]
        return v
    
    @validator("secret_key")
    def validate_secret_key(cls, v):
        """Ensure secret key is at least 32 characters long."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("postgres_url")
    def validate_postgres_url(cls, v):
        """Validate PostgreSQL connection URL format."""
        if not v.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise ValueError("POSTGRES_URL must start with postgresql:// or postgresql+psycopg2://")
        return v
    
    @validator("redis_url")
    def validate_redis_url(cls, v):
        """Validate Redis connection URL format."""
        if not v.startswith("redis://"):
            raise ValueError("REDIS_URL must start with redis://")
        return v
    
    @validator("slack_bot_token")
    def validate_slack_bot_token(cls, v):
        """Validate Slack bot token format."""
        if not v.startswith("xoxb-"):
            raise ValueError("SLACK_BOT_TOKEN must start with xoxb-")
        return v
    
    @validator("slack_app_level_token")
    def validate_slack_app_level_token(cls, v):
        """Validate Slack app level token format."""
        if not v.startswith("xapp-"):
            raise ValueError("SLACK_APP_LEVEL_TOKEN must start with xapp-")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def is_production() -> bool:
    """Check if running in production environment."""
    return settings.app_env.lower() == "prod"


def is_development() -> bool:
    """Check if running in development environment."""
    return settings.app_env.lower() == "dev"


def is_testing() -> bool:
    """Check if running in testing environment."""
    return settings.app_env.lower() == "test" 