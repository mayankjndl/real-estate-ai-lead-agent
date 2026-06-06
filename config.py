import logging
import os
import json
from pydantic_settings import BaseSettings, SettingsConfigDict
import boto3
from botocore.exceptions import ClientError

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
    REDIS_URL: str = "redis://localhost:6379/0"

    # Model configuration — gemini-3.1-flash-lite is the current test model.
    # Supports function calling, tool use, and multi-turn context.
    # Uses the same google-generativeai SDK interface as gemini-2.5-flash.
    # To revert: set GEMINI_MODEL=gemini-2.5-flash in .env
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    # Follow-up system settings
    # TEST MODE: Set FOLLOW_UP_TEST_MODE=true in .env to compress all timings.
    # Day 0 = 1 min, Day 1 = 2 min, Day 3 = 3 min, Day 7 = 4 min
    # Production values: FOLLOW_UP_DELAY_MINUTES=30, hour gaps are 24/48/96
    FOLLOW_UP_DELAY_MINUTES: int = 30
    FOLLOW_UP_MAX_COUNT: int = 2
    USE_AI_FOLLOWUPS: bool = False
    FOLLOW_UP_TEST_MODE: bool = False
    FOLLOW_UP_DLQ_TEST: bool = False  # Set true alongside TEST_MODE to force a DLQ entry for QA

    # Twilio API credentials
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Production flag — set to true on Render
    IS_PRODUCTION: bool = False

    # AWS Secrets Manager
    AWS_REGION: str = ""
    AWS_SECRET_NAME: str = ""

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

def fetch_aws_secrets(secret_name: str, region_name: str) -> dict:
    """Fetch secure variables from AWS Secrets Manager."""
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        if 'SecretString' in get_secret_value_response:
            return json.loads(get_secret_value_response['SecretString'])
    except ClientError as e:
        _cfg_logger.error(f"Failed to fetch AWS Secrets: {e}")
    return {}

settings = Settings()

# Populate from AWS Secrets Manager if configured
if settings.AWS_REGION and settings.AWS_SECRET_NAME:
    _cfg_logger.info(f"Loading credentials from AWS Secrets Manager: {settings.AWS_SECRET_NAME}")
    aws_secrets = fetch_aws_secrets(settings.AWS_SECRET_NAME, settings.AWS_REGION)
    for key, value in aws_secrets.items():
        if hasattr(settings, key):
            setattr(settings, key, value)

# Startup warning so missing secrets are immediately visible in logs
if not settings.GEMINI_API_KEY:
    _cfg_logger.warning("GEMINI_API_KEY is not set — AI responses will fail.")
if not settings.CLIENT_KEY_A:
    _cfg_logger.warning("CLIENT_KEY_A is not set — /leads and /analytics will reject all requests.")