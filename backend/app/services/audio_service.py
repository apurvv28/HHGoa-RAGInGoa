"""
Voice Service Client for Audio I/O.
STRICTLY uses Sarvam AI API or ElevenLabs API for Speech-To-Text (STT) and Text-To-Speech (TTS).
Uses the official sarvamai Python SDK for Sarvam AI calls.
"""

import io
import time
import logging
import base64
from typing import Tuple
import httpx
from backend.app.config import settings

logger = logging.getLogger(__name__)


class SarvamAudioClient:
    """Sarvam AI Voice API Client using the official sarvamai SDK."""

    SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

    def __init__(self, api_key: str = settings.SARVAM_API_KEY):
        self.api_key = api_key
        self._sdk_client = None

    def _get_sdk_client(self):
        """Lazy-initialize the sarvamai SDK client."""
        if self._sdk_client is None:
            from sarvamai import SarvamAI
            self._sdk_client = SarvamAI(api_subscription_key=self.api_key)
        return self._sdk_client

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.webm", language_code: str = "hi-IN") -> Tuple[str, float]:
        """
        Transcribes audio file bytes using Sarvam AI saaras:v4 STT model via official SDK.
        The SDK handles audio format differences (webm, wav, mp3, etc.) automatically.
        """
        start_time = time.perf_counter()

        if not self.api_key or not self.api_key.strip():
            logger.warning("SARVAM_API_KEY not configured. Cannot transcribe.")
            return "", (time.perf_counter() - start_time) * 1000

        try:
            client = self._get_sdk_client()
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = filename  # SDK uses filename to detect format

            response = client.speech_to_text.transcribe(
                file=audio_file,
                model="saaras:v4",
                language_code=language_code if language_code else "hi-IN",
                mode="transcribe",
                input_audio_codec="webm",
            )

            transcript = getattr(response, "transcript", "") or ""
            transcript = transcript.strip()
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Sarvam AI STT transcribed: '{transcript}' in {latency_ms:.2f}ms")
            return transcript, latency_ms

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Sarvam STT SDK call failed: {e}")
            return "", latency_ms

    def synthesize_speech(self, text: str, target_language: str = "hi-IN") -> Tuple[bytes, float]:
        """Synthesizes text into audio bytes using Sarvam AI bulbul:v2 TTS via official SDK."""
        start_time = time.perf_counter()

        if not self.api_key or not self.api_key.strip():
            logger.warning("SARVAM_API_KEY not configured. Returning empty audio bytes.")
            return b"", (time.perf_counter() - start_time) * 1000

        try:
            client = self._get_sdk_client()
            response = client.text_to_speech.convert(
                text=text,
                language_code=target_language if target_language else "hi-IN",
                speaker="anushka",
                model="bulbul:v2",
                pace=1.0,
                loudness=1.5,
                speech_sample_rate=22050,
                enable_preprocessing=True,
            )

            # SDK response has audios list with base64-encoded strings
            audios = getattr(response, "audios", [])
            if audios and audios[0]:
                audio_bytes = base64.b64decode(audios[0])
            else:
                audio_bytes = b""

            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Sarvam AI TTS synthesized in {latency_ms:.2f}ms")
            return audio_bytes, latency_ms

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Sarvam TTS SDK call failed: {e}")
            return b"", latency_ms


class ElevenLabsAudioClient:
    """ElevenLabs Voice API Client for High-Quality TTS."""

    def __init__(self, api_key: str = settings.ELEVENLABS_API_KEY):
        self.api_key = api_key

    def synthesize_speech(self, text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> Tuple[bytes, float]:
        """Synthesizes speech via ElevenLabs API."""
        start_time = time.perf_counter()

        if not self.api_key:
            logger.warning("ELEVENLABS_API_KEY not set. Returning empty audio bytes.")
            return b"", (time.perf_counter() - start_time) * 1000

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code != 200:
                    logger.error(f"ElevenLabs TTS {response.status_code}: {response.text[:200]}")
                response.raise_for_status()
                latency_ms = (time.perf_counter() - start_time) * 1000
                return response.content, latency_ms
        except Exception as e:
            logger.error(f"ElevenLabs TTS call failed: {e}")
            return b"", (time.perf_counter() - start_time) * 1000


class AudioService:
    """Facade service for STT and TTS choosing between Sarvam AI and ElevenLabs."""

    def __init__(self):
        self.sarvam_client = SarvamAudioClient()
        self.elevenlabs_client = ElevenLabsAudioClient()

    def speech_to_text(self, audio_bytes: bytes, filename: str = "input.webm", language: str = "hi-IN") -> Tuple[str, float]:
        """Transcribes input audio using Sarvam AI STT via official SDK."""
        return self.sarvam_client.transcribe_audio(audio_bytes, filename=filename, language_code=language)

    def text_to_speech(self, text: str, provider: str = "sarvam", language: str = "hi-IN") -> Tuple[bytes, float]:
        """Synthesizes speech using designated voice provider."""
        if provider.lower() == "elevenlabs" and settings.ELEVENLABS_API_KEY:
            return self.elevenlabs_client.synthesize_speech(text)
        return self.sarvam_client.synthesize_speech(text, target_language=language)


audio_service = AudioService()
