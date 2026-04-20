import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

_cfg_logger = logging.getLogger("config")

class Settings(BaseSettings):
    """
    Secure configuration management using Pydantic.
    ALL secrets must be supplied via environment variables or a .env file.
    No credentials are hardcoded in this file.
    """
    GEMINI_API_KEY: str = ""

    # Client API keys — must be set in .env or Render environment variables.
    # No defaults: an empty key means the endpoint will reject all requests.
    API_AUTH_KEY: str = ""
    CLIENT_KEY_A: str = ""
    CLIENT_KEY_B: str = ""

    # Database Settings
    DATABASE_URL: str = "sqlite:///./real_estate_agent.db"

    # Model configuration
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Follow-up system settings
    FOLLOW_UP_DELAY_MINUTES: int = 3
    FOLLOW_UP_MAX_COUNT: int = 2
    USE_AI_FOLLOWUPS: bool = False

    # Twilio API credentials
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def CLIENT_KEYS(self) -> dict:
        """
        Assembles client→key mapping at runtime from individual env vars.
        Never hardcoded — sourced from CLIENT_KEY_A and CLIENT_KEY_B in .env.
        """
        return {
            "client_A": self.CLIENT_KEY_A,
            "client_B": self.CLIENT_KEY_B,
        }


settings = Settings()

# Startup warning so missing secrets are immediately visible in logs
if not settings.GEMINI_API_KEY:
    _cfg_logger.warning("GEMINI_API_KEY is not set — AI responses will fail.")
if not settings.CLIENT_KEY_A:
    _cfg_logger.warning("CLIENT_KEY_A is not set — /leads and /analytics will reject all requests.")

