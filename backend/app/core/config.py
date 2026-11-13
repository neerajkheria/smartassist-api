from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartAssist AI"
    VERSION: str = "0.2.0"
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LEARNER_ID: str = os.getenv("LEARNER_ID", "default-user")

    # Azure OpenAI Settings
    AZURE_OPENAI_ENDPOINT: str = "https://eastus2.api.cognitive.microsoft.com/"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-5.1"
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"

    # Model Defaults
    MAX_OUTPUT_TOKENS: int = 800
    DEFAULT_TEMPERATURE: float = 0.3

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()