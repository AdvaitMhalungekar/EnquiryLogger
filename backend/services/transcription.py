import io
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional
from backend.config import settings

logger = logging.getLogger(__name__)


class TranscriptionService(ABC):
    """Provider-agnostic interface for audio transcription."""

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, filename: str = "enquiry_audio.webm") -> str:
        """
        Transcribes the given audio bytes and returns the text transcript.
        Must handle English and Hinglish (Hindi-English mix) speech.
        """
        pass


class GroqWhisperTranscriptionService(TranscriptionService):
    """
    Transcription service powered by Groq's fast Whisper API (whisper-large-v3).
    Supports English and Hinglish accents and speech patterns seamlessly.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_WHISPER_MODEL

    async def transcribe(self, audio_bytes: bytes, filename: str = "enquiry_audio.webm") -> str:
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY is not configured. Please set GROQ_API_KEY in your .env file."
            )

        from groq import Groq

        client = Groq(api_key=self.api_key)

        # Groq client audio transcription accepts a tuple of (filename, bytes_or_buffer, [content_type])
        # We pass it in memory to avoid writing temporary files to disk.
        # Add a prompt hint to optimize for Hinglish / Indian English enquiry context.
        prompt_hint = (
            "Voice enquiry in English or Hinglish about courses, college student, fresher, "
            "working professional, career switcher, AI/ML, Generative AI, Data Science, "
            "AI Agents, Python, Power BI."
        )

        try:
            # Determine appropriate mime/extension
            ext = os.path.splitext(filename)[1].lower() or ".webm"
            file_tuple = (f"audio{ext}", audio_bytes)

            transcription = client.audio.transcriptions.create(
                file=file_tuple,
                model=self.model,
                prompt=prompt_hint,
                temperature=0.0,
                response_format="json"
            )
            text = transcription.text if hasattr(transcription, "text") else str(transcription)
            return text.strip()
        except Exception as e:
            logger.error(f"Error during Groq Whisper transcription: {e}")
            raise RuntimeError(f"Transcription failed: {str(e)}")


class OpenAIWhisperTranscriptionService(TranscriptionService):
    """Fallback transcription service using OpenAI Whisper."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY

    async def transcribe(self, audio_bytes: bytes, filename: str = "enquiry_audio.webm") -> str:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            ext = os.path.splitext(filename)[1].lower() or ".webm"
            file_tuple = (f"audio{ext}", audio_bytes)

            transcription = client.audio.transcriptions.create(
                file=file_tuple,
                model="whisper-1",
                temperature=0.0
            )
            return transcription.text.strip()
        except Exception as e:
            logger.error(f"Error during OpenAI Whisper transcription: {e}")
            raise RuntimeError(f"Transcription failed: {str(e)}")


class MockTranscriptionService(TranscriptionService):
    """Mock transcription for testing or offline environments."""

    def __init__(self, mock_transcript: str = "Hi, my name is Priya Sharma. I am a fresher and I want to learn Python and Generative AI."):
        self.mock_transcript = mock_transcript

    async def transcribe(self, audio_bytes: bytes, filename: str = "enquiry_audio.webm") -> str:
        return self.mock_transcript


def get_transcription_service() -> TranscriptionService:
    """Factory to instantiate the configured transcription service."""
    provider = settings.TRANSCRIPTION_PROVIDER.lower().strip()
    if provider == "groq":
        return GroqWhisperTranscriptionService()
    elif provider == "openai":
        return OpenAIWhisperTranscriptionService()
    elif provider == "mock":
        return MockTranscriptionService()
    else:
        # Default to Groq
        return GroqWhisperTranscriptionService()
