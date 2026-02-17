"""
Voice Transcriber Module
Handles audio-to-text transcription using Groq Whisper API (primary)
with optional local Whisper fallback.
"""

import io
import logging
import time
from dataclasses import dataclass, field
from typing import Literal

from src.config import get_config

logger = logging.getLogger(__name__)

# Supported audio formats
SUPPORTED_FORMATS = {"wav", "mp3", "m4a", "webm", "ogg", "flac", "mp4", "mpeg", "mpga"}

# Max file size: 25MB (Groq/Whisper limit)
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024


@dataclass
class TranscriptionResult:
    """Result of an audio transcription."""
    text: str
    language: str = "es"
    duration_seconds: float = 0.0
    confidence: float | None = None
    provider: str = "groq"
    processing_time_ms: int = 0
    success: bool = True
    error: str | None = None


class VoiceTranscriber:
    """
    Transcribes audio to text using Groq Whisper API.
    
    Usage:
        transcriber = VoiceTranscriber()
        result = await transcriber.transcribe(audio_bytes, "wav")
    """

    def __init__(self):
        config = get_config()
        self._provider = config.voice.provider
        self._groq_api_key = config.voice.groq_api_key
        self._model = config.voice.whisper_model
        self._language = config.voice.language
        self._max_duration = config.voice.max_audio_duration_seconds

    async def transcribe(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
        language: str | None = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format (wav, mp3, m4a, webm, ogg, flac)
            language: Language hint (default: from config, typically "es")
            
        Returns:
            TranscriptionResult with transcribed text and metadata
        """
        start_time = time.time()
        lang = language or self._language

        # Validate input
        validation_error = self._validate_audio(audio_data, audio_format)
        if validation_error:
            return TranscriptionResult(
                text="",
                success=False,
                error=validation_error,
                provider=self._provider,
            )

        try:
            if self._provider == "groq":
                result = await self._transcribe_groq(audio_data, audio_format, lang)
            else:
                result = TranscriptionResult(
                    text="",
                    success=False,
                    error=f"Provider '{self._provider}' no soportado. Usa 'groq'.",
                    provider=self._provider,
                )
        except Exception as e:
            logger.error(f"Transcription failed with {self._provider}: {e}")
            result = TranscriptionResult(
                text="",
                success=False,
                error=f"Error de transcripción: {str(e)}",
                provider=self._provider,
            )

        # Record processing time
        result.processing_time_ms = int((time.time() - start_time) * 1000)

        if result.success:
            logger.info(
                f"Transcription OK: {len(result.text)} chars, "
                f"{result.processing_time_ms}ms, provider={result.provider}"
            )
        else:
            logger.warning(f"Transcription failed: {result.error}")

        return result

    def _validate_audio(self, audio_data: bytes, audio_format: str) -> str | None:
        """
        Validate audio data before processing.
        
        Returns:
            Error message string if invalid, None if valid
        """
        if not audio_data:
            return "No se recibió audio. Por favor graba un mensaje de voz."

        # Check format
        fmt = audio_format.lower().lstrip(".")
        if fmt not in SUPPORTED_FORMATS:
            return (
                f"Formato de audio '{fmt}' no soportado. "
                f"Formatos válidos: {', '.join(sorted(SUPPORTED_FORMATS))}"
            )

        # Check file size
        if len(audio_data) > MAX_FILE_SIZE_BYTES:
            size_mb = len(audio_data) / (1024 * 1024)
            return f"Audio demasiado grande ({size_mb:.1f} MB). Máximo: 25 MB."

        # Check minimum size (likely empty/corrupt)
        if len(audio_data) < 100:
            return "El audio es demasiado corto o está vacío."

        return None

    async def _transcribe_groq(
        self,
        audio_data: bytes,
        audio_format: str,
        language: str,
    ) -> TranscriptionResult:
        """
        Transcribe audio using Groq Whisper API.
        
        Uses httpx for async HTTP calls to Groq's OpenAI-compatible API.
        """
        import httpx

        if not self._groq_api_key:
            return TranscriptionResult(
                text="",
                success=False,
                error="GROQ_API_KEY no configurada. Agrega tu API key en .env",
                provider="groq",
            )

        fmt = audio_format.lower().lstrip(".")
        filename = f"audio.{fmt}"

        # Build multipart form data
        files = {
            "file": (filename, audio_data, f"audio/{fmt}"),
        }
        data = {
            "model": self._model,
            "language": language,
            "response_format": "verbose_json",
            "temperature": 0.0,
        }

        headers = {
            "Authorization": f"Bearer {self._groq_api_key}",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
            )

            if response.status_code != 200:
                error_detail = response.text[:200]
                return TranscriptionResult(
                    text="",
                    success=False,
                    error=f"Error de Groq API ({response.status_code}): {error_detail}",
                    provider="groq",
                )

            result_json = response.json()

            text = result_json.get("text", "").strip()
            duration = result_json.get("duration", 0.0)
            detected_lang = result_json.get("language", language)

            if not text:
                return TranscriptionResult(
                    text="",
                    success=False,
                    error="No se detectó habla en el audio. Intenta de nuevo.",
                    provider="groq",
                    duration_seconds=duration,
                    language=detected_lang,
                )

            return TranscriptionResult(
                text=text,
                language=detected_lang,
                duration_seconds=duration,
                provider="groq",
                success=True,
            )

    def is_enabled(self) -> bool:
        """Check if voice transcription is enabled and configured."""
        config = get_config()
        return config.voice.enabled and bool(self._groq_api_key)
