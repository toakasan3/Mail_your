"""
MailGuard OSS - Configuration Module
Pydantic v2 settings with startup validation
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from typing import Optional


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str  # Service key, never anon key
    
    # Redis Configuration
    REDIS_URL: str
    
    # Encryption & JWT
    ENCRYPTION_KEY: str  # Exactly 64 hex chars = 32 bytes for AES-256
    JWT_SECRET: str  # Minimum 64 characters
    JWT_EXPIRY_MINUTES: int = 10
    
    # Environment
    ENV: str = "development"
    PORT: int = 3000
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ADMIN_UID: Optional[int] = None
    
    # Rate Limiting Defaults
    RATE_LIMIT_EMAIL_PER_HOUR: int = 10
    RATE_LIMIT_API_KEY_PER_HOUR: int = 1000
    RATE_LIMIT_IP_PER_15MIN: int = 100
    RATE_LIMIT_PROJECT_PER_DAY: int = 10000
    RATE_LIMIT_SMTP_PER_DAY: int = 500
    
    # OTP Defaults
    OTP_LENGTH: int = 6
    OTP_EXPIRY_SECONDS: int = 600
    OTP_MAX_ATTEMPTS: int = 5
    
    @field_validator('ENCRYPTION_KEY')
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """Validate ENCRYPTION_KEY is exactly 64 hex characters (32 bytes)"""
        if len(v) != 64:
            raise ValueError('ENCRYPTION_KEY must be 64 hex chars (32 bytes)')
        try:
            bytes.fromhex(v)
        except ValueError:
            raise ValueError('ENCRYPTION_KEY must be valid hex')
        return v
    
    @field_validator('JWT_SECRET')
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT_SECRET is at least 64 characters"""
        if len(v) < 64:
            raise ValueError('JWT_SECRET must be at least 64 characters')
        return v
    
    @field_validator('SUPABASE_URL')
    @classmethod
    def validate_supabase_url(cls, v: str) -> str:
        """Validate Supabase URL format"""
        if not v.startswith('https://') or '.supabase.co' not in v:
            raise ValueError('SUPABASE_URL must be a valid Supabase URL (https://xxx.supabase.co)')
        return v
    
    @field_validator('REDIS_URL')
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format"""
        if not v.startswith(('redis://', 'rediss://')):
            raise ValueError('REDIS_URL must start with redis:// or rediss://')
        return v
    
    @model_validator(mode='after')
    def validate_telegram_config(self) -> 'Settings':
        """Validate Telegram configuration is present when needed"""
        # Telegram config is required for bot service
        return self
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENV.lower() == 'production'
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENV.lower() == 'development'
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance - validates on import
settings = Settings()