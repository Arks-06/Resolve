from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Centralized configuration registry.
    Validates environment variables at application startup.
    """
    database_url: str 
    encryption_master_key: str
    redis_url: str 
    groq_api_key: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Instantiate a global configuration object for dependency injection
settings = Settings() # type: ignore