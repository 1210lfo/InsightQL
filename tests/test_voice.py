"""
Tests for Voice Transcription Module
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.voice.transcriber import (
    VoiceTranscriber,
    TranscriptionResult,
    SUPPORTED_FORMATS,
    MAX_FILE_SIZE_BYTES,
)


# =============================================================================
# Validation Tests
# =============================================================================


class TestVoiceValidation:
    """Tests for audio input validation."""

    def setup_method(self):
        """Setup transcriber with mocked config."""
        with patch("src.voice.transcriber.get_config") as mock_config:
            mock_config.return_value.voice.provider = "groq"
            mock_config.return_value.voice.groq_api_key = "test-key"
            mock_config.return_value.voice.whisper_model = "whisper-large-v3-turbo"
            mock_config.return_value.voice.language = "es"
            mock_config.return_value.voice.max_audio_duration_seconds = 60
            mock_config.return_value.voice.enabled = True
            self.transcriber = VoiceTranscriber()

    def test_validate_empty_audio(self):
        error = self.transcriber._validate_audio(b"", "wav")
        assert error is not None
        assert "No se recibió audio" in error

    def test_validate_too_small_audio(self):
        error = self.transcriber._validate_audio(b"tiny", "wav")
        assert error is not None
        assert "demasiado corto" in error

    def test_validate_unsupported_format(self):
        audio = b"x" * 1000
        error = self.transcriber._validate_audio(audio, "txt")
        assert error is not None
        assert "no soportado" in error

    def test_validate_too_large_audio(self):
        audio = b"x" * (MAX_FILE_SIZE_BYTES + 1)
        error = self.transcriber._validate_audio(audio, "wav")
        assert error is not None
        assert "demasiado grande" in error

    def test_validate_valid_audio(self):
        audio = b"x" * 1000
        for fmt in ["wav", "mp3", "m4a", "webm", "ogg", "flac"]:
            error = self.transcriber._validate_audio(audio, fmt)
            assert error is None, f"Format {fmt} should be valid"

    def test_validate_format_with_dot(self):
        audio = b"x" * 1000
        error = self.transcriber._validate_audio(audio, ".wav")
        assert error is None

    def test_supported_formats_exist(self):
        assert "wav" in SUPPORTED_FORMATS
        assert "mp3" in SUPPORTED_FORMATS
        assert "webm" in SUPPORTED_FORMATS
        assert "ogg" in SUPPORTED_FORMATS


# =============================================================================
# Transcription Tests
# =============================================================================


class TestVoiceTranscription:
    """Tests for transcription functionality."""

    def setup_method(self):
        with patch("src.voice.transcriber.get_config") as mock_config:
            mock_config.return_value.voice.provider = "groq"
            mock_config.return_value.voice.groq_api_key = "test-key"
            mock_config.return_value.voice.whisper_model = "whisper-large-v3-turbo"
            mock_config.return_value.voice.language = "es"
            mock_config.return_value.voice.max_audio_duration_seconds = 60
            mock_config.return_value.voice.enabled = True
            self.transcriber = VoiceTranscriber()

    @pytest.mark.asyncio
    async def test_transcribe_empty_returns_error(self):
        result = await self.transcriber.transcribe(b"", "wav")
        assert not result.success
        assert "No se recibió audio" in result.error

    @pytest.mark.asyncio
    async def test_transcribe_invalid_format_returns_error(self):
        result = await self.transcriber.transcribe(b"x" * 1000, "txt")
        assert not result.success
        assert "no soportado" in result.error

    @pytest.mark.asyncio
    async def test_transcribe_groq_success(self):
        """Test successful Groq transcription with mocked HTTP."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "¿Cuál es el precio promedio de calzado?",
            "language": "es",
            "duration": 3.5,
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_class.return_value = mock_client

            result = await self.transcriber.transcribe(b"x" * 1000, "wav")

            assert result.success
            assert result.text == "¿Cuál es el precio promedio de calzado?"
            assert result.language == "es"
            assert result.duration_seconds == 3.5
            assert result.provider == "groq"
            assert result.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_transcribe_groq_api_error(self):
        """Test Groq API error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_class.return_value = mock_client

            result = await self.transcriber.transcribe(b"x" * 1000, "wav")

            assert not result.success
            assert "429" in result.error

    @pytest.mark.asyncio
    async def test_transcribe_no_speech_detected(self):
        """Test when audio has no detectable speech."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "",
            "language": "es",
            "duration": 2.0,
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_class.return_value = mock_client

            result = await self.transcriber.transcribe(b"x" * 1000, "wav")

            assert not result.success
            assert "No se detectó habla" in result.error


# =============================================================================
# TranscriptionResult Tests
# =============================================================================


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass."""

    def test_default_values(self):
        result = TranscriptionResult(text="hola")
        assert result.text == "hola"
        assert result.language == "es"
        assert result.success is True
        assert result.error is None
        assert result.provider == "groq"

    def test_error_result(self):
        result = TranscriptionResult(
            text="",
            success=False,
            error="Something failed",
        )
        assert result.text == ""
        assert not result.success
        assert result.error == "Something failed"


# =============================================================================
# Integration Tests (requires GROQ_API_KEY)
# =============================================================================


class TestVoiceEnabled:
    """Tests for enabled/disabled state."""

    def test_is_enabled_with_key(self):
        with patch("src.voice.transcriber.get_config") as mock_config:
            mock_config.return_value.voice.provider = "groq"
            mock_config.return_value.voice.groq_api_key = "test-key"
            mock_config.return_value.voice.whisper_model = "whisper-large-v3-turbo"
            mock_config.return_value.voice.language = "es"
            mock_config.return_value.voice.max_audio_duration_seconds = 60
            mock_config.return_value.voice.enabled = True
            t = VoiceTranscriber()
            assert t.is_enabled()

    def test_is_disabled_without_key(self):
        with patch("src.voice.transcriber.get_config") as mock_config:
            mock_config.return_value.voice.provider = "groq"
            mock_config.return_value.voice.groq_api_key = ""
            mock_config.return_value.voice.whisper_model = "whisper-large-v3-turbo"
            mock_config.return_value.voice.language = "es"
            mock_config.return_value.voice.max_audio_duration_seconds = 60
            mock_config.return_value.voice.enabled = True
            t = VoiceTranscriber()
            assert not t.is_enabled()

    def test_is_disabled_by_config(self):
        with patch("src.voice.transcriber.get_config") as mock_config:
            mock_config.return_value.voice.provider = "groq"
            mock_config.return_value.voice.groq_api_key = "test-key"
            mock_config.return_value.voice.whisper_model = "whisper-large-v3-turbo"
            mock_config.return_value.voice.language = "es"
            mock_config.return_value.voice.max_audio_duration_seconds = 60
            mock_config.return_value.voice.enabled = False
            t = VoiceTranscriber()
            assert not t.is_enabled()
