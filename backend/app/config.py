"""Application configuration loaded from environment variables / .env file."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Security
    SECRET_KEY: str = "change-me-to-a-long-random-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    # Database
    DATABASE_URL: str = "sqlite:///./societyhub.db"

    # Branding
    APP_NAME: str = "SocietyHub"

    # CORS
    CORS_ORIGINS: str = "*"

    # OTP / SMS
    SMS_PROVIDER: str = "console"  # console | twilio | msg91
    REQUIRE_OTP: bool = True  # when False, signup/login skip OTP verification
    OTP_EXPIRY_MINUTES: int = 5
    OTP_LENGTH: int = 6
    OTP_RESEND_COOLDOWN_SECONDS: int = 30
    OTP_MAX_ATTEMPTS: int = 5
    DEFAULT_COUNTRY_CODE: str = "+91"

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM: str = ""

    # MSG91
    MSG91_AUTH_KEY: str = ""
    MSG91_SENDER: str = ""
    MSG91_TEMPLATE_ID: str = ""
    MSG91_ROUTE: str = "4"

    # Seeded admin
    DEFAULT_ADMIN_NAME: str = "IT Support"
    DEFAULT_ADMIN_MOBILE: str = "+919999999999"
    DEFAULT_ADMIN_PASSWORD: str = "ChangeMe@123"

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
