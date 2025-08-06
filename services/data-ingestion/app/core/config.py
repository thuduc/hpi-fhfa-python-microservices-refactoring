"""Configuration settings for Data Ingestion Service."""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    DEBUG: bool = Field(default=False, description="Debug mode")
    SERVICE_NAME: str = Field(default="data-ingestion", description="Service name")
    API_V1_STR: str = Field(default="/api/v1", description="API version prefix")
    
    # Server
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8001, description="Server port")
    WORKERS: int = Field(default=1, description="Number of worker processes")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://rsai:rsai_password@localhost:5432/rsai_ingestion",
        description="Database connection URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow connections")
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_MAX_CONNECTIONS: int = Field(default=10, description="Redis max connections")
    
    # Message Queue
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL"
    )
    
    # File Upload
    MAX_FILE_SIZE_MB: int = Field(default=100, description="Maximum file size in MB")
    UPLOAD_DIR: str = Field(default="/tmp/rsai-uploads", description="File upload directory")
    ALLOWED_FILE_EXTENSIONS: List[str] = Field(
        default=[".csv", ".parquet", ".xlsx"],
        description="Allowed file extensions"
    )
    
    # Data Processing
    BATCH_SIZE: int = Field(default=10000, description="Default batch size for processing")
    MAX_RECORDS_PER_REQUEST: int = Field(default=50000, description="Maximum records per API request")
    
    # External Services
    VALIDATION_SERVICE_URL: str = Field(
        default="http://localhost:8002",
        description="Data Validation Service URL"
    )
    GEOGRAPHY_SERVICE_URL: str = Field(
        default="http://localhost:8003",
        description="Geography Service URL"
    )
    
    # Monitoring
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    ENABLE_METRICS: bool = Field(default=True, description="Enable Prometheus metrics")
    
    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT tokens"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration in minutes"
    )
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, description="Rate limit per minute")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()