import io
import wave
from typing import Callable, List, Optional

import requests

from audio import CHANNELS, SAMPLE_RATE, SAMPLE_WIDTH
from providers.base import ISO_639_1_LANGUAGES, Provider

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_MODEL = "whisper-large-v3-turbo"


class GroqProvider(Provider):
    name = "groq"
    display_name = "Groq"
    streaming = False
    # Groq's real-time-oriented Whisper: ~216x realtime, multilingual, accuracy
    # comparable to whisper-large-v3.
    MODEL_LABEL = DEFAULT_MODEL
    LANGUAGES = ISO_639_1_LANGUAGES

    def configure(
        self,
        api_key: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
        keyterms: Optional[List[str]] = None,
    ) -> None:
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL
        self.language = language
        self.prompt = ", ".join(keyterms) if keyterms else None
        self._buffer = bytearray()

    def start(
        self,
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._buffer = bytearray()

    def feed_audio(self, chunk: bytes) -> None:
        self._buffer.extend(chunk)

    def stop(self) -> str:
        wav_bytes = self._to_wav(bytes(self._buffer))
        files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
        data = {"model": self.model}
        if self.language:
            data["language"] = self.language
        if self.prompt:
            data["prompt"] = self.prompt
        headers = {"Authorization": f"Bearer {self.api_key}"}

        response = requests.post(GROQ_URL, headers=headers, files=files, data=data)
        response.raise_for_status()
        return response.json()["text"]

    @staticmethod
    def _to_wav(pcm_bytes: bytes) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(SAMPLE_WIDTH)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(pcm_bytes)
        return buf.getvalue()
