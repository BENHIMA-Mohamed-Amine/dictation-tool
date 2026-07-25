import queue
import threading
from typing import Callable, List, Optional

import riva.client

from audio import CHANNELS, SAMPLE_RATE
from providers.base import Provider

NVCF_URI = "grpc.nvcf.nvidia.com:443"
NEMOTRON_ASR_STREAMING_FUNCTION_ID = "bb0837de-8c7b-481f-9ec8-ef5663e9c1fa"
DEFAULT_LANGUAGE = "en-US"
WORD_BOOST_SCORE = 20.0

_STOP_SENTINEL = None


class NvidiaProvider(Provider):
    name = "nvidia"
    display_name = "NVIDIA"
    streaming = True
    # No model choice: the hosted NIM function id above *is* the model.
    MODELS = []
    # Riva requires an explicit language_code, so there's no auto-detect entry
    # here — unlike Groq/Soniox, omitting the language isn't an option. Whether
    # this function accepts "multi" for auto-detection is unverified (needs a
    # live API key); add it once confirmed.
    LANGUAGES = [
        ("English (US)", "en-US"),
        ("French", "fr-FR"),
        ("Spanish", "es-US"),
        ("German", "de-DE"),
    ]

    def configure(
        self,
        api_key: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
        keyterms: Optional[List[str]] = None,
    ) -> None:
        self.api_key = api_key
        self.language = language or DEFAULT_LANGUAGE
        self.keyterms = keyterms or []

    def start(
        self,
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._on_partial = on_partial
        self._on_final = on_final
        self._final_text_parts: List[str] = []
        self._audio_queue: "queue.Queue[Optional[bytes]]" = queue.Queue()

        auth = riva.client.Auth(
            uri=NVCF_URI,
            use_ssl=True,
            metadata_args=[
                ["function-id", NEMOTRON_ASR_STREAMING_FUNCTION_ID],
                ["authorization", f"Bearer {self.api_key}"],
            ],
        )
        self._service = riva.client.ASRService(auth)

        recognition_config = riva.client.RecognitionConfig(
            encoding=riva.client.AudioEncoding.LINEAR_PCM,
            sample_rate_hertz=SAMPLE_RATE,
            language_code=self.language,
            max_alternatives=1,
            audio_channel_count=CHANNELS,
            enable_automatic_punctuation=True,
        )
        streaming_config = riva.client.StreamingRecognitionConfig(config=recognition_config, interim_results=True)
        if self.keyterms:
            riva.client.add_word_boosting_to_config(streaming_config, self.keyterms, WORD_BOOST_SCORE)

        self._listener_thread = threading.Thread(
            target=self._listen, args=(streaming_config,), daemon=True
        )
        self._listener_thread.start()

    def _audio_chunks(self):
        while True:
            chunk = self._audio_queue.get()
            if chunk is _STOP_SENTINEL:
                return
            yield chunk

    def _listen(self, streaming_config) -> None:
        try:
            for response in self._service.streaming_response_generator(
                audio_chunks=self._audio_chunks(), streaming_config=streaming_config
            ):
                for result in response.results:
                    if not result.alternatives:
                        continue
                    text = result.alternatives[0].transcript
                    if result.is_final:
                        self._final_text_parts.append(text)
                        if self._on_final:
                            self._on_final(text)
                    elif self._on_partial:
                        self._on_partial(text)
        except Exception as exc:
            # The request stream ends (cleanly) once stop() pushes the
            # sentinel — the gRPC call can still raise while that's in
            # flight, which is expected during shutdown. But a real error
            # (bad auth, model not accessible, etc.) would otherwise vanish
            # silently — a session that produces zero transcript with no
            # visible cause. Print it so it's at least not invisible.
            print(f"NvidiaProvider error: {exc}")

    def feed_audio(self, chunk: bytes) -> None:
        self._audio_queue.put(chunk)

    def stop(self) -> str:
        self._audio_queue.put(_STOP_SENTINEL)
        self._listener_thread.join(timeout=5)
        return "".join(self._final_text_parts)
