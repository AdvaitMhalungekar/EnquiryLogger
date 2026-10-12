import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Groq API Configuration (for both LLM extraction and Whisper transcription)
    GROQ_API_KEY: str = Field(default="", description="Groq API key")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile", description="Groq LLM model name")
    GROQ_WHISPER_MODEL: str = Field(default="whisper-large-v3", description="Groq Whisper model")

    # Transcription provider choice: "groq", "openai", "mock"
    TRANSCRIPTION_PROVIDER: str = Field(default="groq", description="Transcription provider")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key (optional fallback)")

    # Google Sheets Configuration
    GOOGLE_SHEET_ID: str = Field(default="", description="Google Sheet ID or URL")
    GOOGLE_SERVICE_ACCOUNT_JSON_PATH: str = Field(
        default="service_account.json",
        description="Path to Google Service Account JSON credentials file"
    )
    GOOGLE_SERVICE_ACCOUNT_JSON_RAW: str = Field(
        default="",
        description="Optional raw JSON string for Google Service Account credentials"
    )
    GOOGLE_SHEET_NAME: str = Field(default="Sheet1", description="Worksheet tab name")

    # Audio limits
    MAX_AUDIO_SIZE_MB: int = Field(default=10, description="Max audio upload size in MB")
    MAX_AUDIO_DURATION_SECONDS: int = Field(default=120, description="Max audio duration in seconds")

    # Timezone for Enquiry Time
    TIMEZONE: str = Field(default="Asia/Kolkata", description="Timezone for enquiry timestamp")

    # App Host / Port
    HOST: str = Field(default="0.0.0.0", description="App server host")
    PORT: int = Field(default=8000, description="App server port")


# Singleton instance
settings = Settings()
