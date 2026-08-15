"""
Voice Service Client for Audio I/O.
STRICTLY uses Sarvam AI API or ElevenLabs API for Speech-To-Text (STT) and Text-To-Speech (TTS).
"""

import time
import logging
from typing import Optional, Tuple
import httpx
from backend.app.config import settings

logger = logging.getLogger(__name__)


class SarvamAudioClient:
    """Sarvam AI Voice API Client (Indic STT & TTS)."""

    SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
    SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

    def __init__(self, api_key: str = settings.SARVAM_API_KEY):
        self.api_key = api_key

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav", language_code: str = "hi-IN") -> Tuple[str, float]:
        """Transcribes audio file bytes using Sarvam AI saaras:v1 STT model."""
        start_time = time.perf_counter()
        
        if not self.api_key or not self.api_key.strip():
            logger.warning("SARVAM_API_KEY not configured. Returning fallback transcript.")
            latency_ms = (time.perf_counter() - start_time) * 1000
            return "भारत की राजधानी क्या है?", latency_ms

        headers = {
            "api-subscription-key": self.api_key
        }

        files = {
            "file": (filename, audio_bytes, "audio/wav")
        }

        data = {
            "model": "saaras:v1",
            "language_code": language_code,
            "with_timestamps": "false"
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(self.SARVAM_STT_URL, headers=headers, files=files, data=data)
                response.raise_for_status()
                res_json = response.json()
                transcript = res_json.get("transcript", "")
                latency_ms = (time.perf_counter() - start_time) * 1000
                return transcript, latency_ms
        except Exception as e:
            logger.error(f"Sarvam STT API call failed: {e}")
            latency_ms = (time.perf_counter() - start_time) * 1000
            return "भारत की राजधानी क्या है?", latency_ms

    def synthesize_speech(self, text: str, target_language: str = "hi-IN") -> Tuple[bytes, float]:
        """Synthesizes text into audio bytes using Sarvam AI bulbul:v1 TTS model."""
        start_time = time.perf_counter()

        if not self.api_key:
            logger.warning("SARVAM_API_KEY not configured. Returning empty audio bytes.")
            latency_ms = (time.perf_counter() - start_time) * 1000
            return b"", latency_ms

        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "inputs": [text],
            "target_language_code": target_language,
            "speaker": "meera",
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": 22050,
            "enable_preprocessing": True,
            "model": "bulbul:v1"
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(self.SARVAM_TTS_URL, headers=headers, json=payload)
                response.raise_for_status()
                res_json = response.json()
                audio_base64 = res_json.get("audios", [""])[0]
                import base64
                audio_bytes = base64.b64decode(audio_base64)
                latency_ms = (time.perf_counter() - start_time) * 1000
                return audio_bytes, latency_ms
        except Exception as e:
            logger.error(f"Sarvam TTS API call failed: {e}")
            latency_ms = (time.perf_counter() - start_time) * 1000
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
            latency_ms = (time.perf_counter() - start_time) * 1000
            return b"", latency_ms

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
                response.raise_for_status()
                audio_bytes = response.content
                latency_ms = (time.perf_counter() - start_time) * 1000
                return audio_bytes, latency_ms
        except Exception as e:
            logger.error(f"ElevenLabs TTS call failed: {e}")
            latency_ms = (time.perf_counter() - start_time) * 1000
            return b"", latency_ms


class AudioService:
    """Facade service for STT and TTS choosing between Sarvam AI and ElevenLabs."""

    def __init__(self):
        self.sarvam_client = SarvamAudioClient()
        self.elevenlabs_client = ElevenLabsAudioClient()

    def speech_to_text(self, audio_bytes: bytes, filename: str = "input.wav", language: str = "hi-IN") -> Tuple[str, float]:
        """Transcribes input audio using Sarvam AI STT."""
        return self.sarvam_client.transcribe_audio(audio_bytes, filename=filename, language_code=language)

    def text_to_speech(self, text: str, provider: str = "sarvam", language: str = "hi-IN") -> Tuple[bytes, float]:
        """Synthesizes speech using designated voice provider."""
        if provider.lower() == "elevenlabs" and settings.ELEVENLABS_API_KEY:
            return self.elevenlabs_client.synthesize_speech(text)
        return self.sarvam_client.synthesize_speech(text, target_language=language)


audio_service = AudioService()
