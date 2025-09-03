"""
    Configuration Management For the Service
"""
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


class Settings(BaseSettings):

    # Application Info
    SERVICE_NAME: str = "Service Name"
    SERVICE_VERSION: str = os.getenv("SERVICE_VERSION", "v0.0.1")
    SERVICE_DESCRIPTION: str= "Service Description"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8010
    LOG_LEVEL: str = "DEBUG"


    """Pydantic Configuration"""

    model_config = ConfigDict(
        env_file=f".env.{ENVIRONMENT}",
        extra="ignore"
    )

settings = Settings()
