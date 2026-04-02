from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Secure configuration management using Pydantic.
    Loads environment variables from a .env file if available.
    """
    GEMINI_API_KEY: str = ""
    # Default API key for client-grade endpoints (Piyush can override via .env)
    API_AUTH_KEY: str = "secret-client-key-123" 
    
    # Multi-client API mapping dict
    CLIENT_KEYS: dict = {
        "client_A": "secret-client-key-123",
        "client_B": "secret-client-B"
    }

    # Database Settings
    DATABASE_URL: str = "sqlite:///./real_estate_agent.db"
    
    # Model configuration
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
