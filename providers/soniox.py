import threading
from typing import Callable, List, Optional

from soniox.client import SonioxClient
from soniox.types import RealtimeSTTConfig, StructuredContext

from audio import CHANNELS, SAMPLE_RATE
from providers.base import Provider

DEFAULT_MODEL = "stt-rt-v5"

# Non-speech control tokens Soniox emits (e.g. end-of-stream markers) — not real words.
CONTROL_TOKENS = {"<fin>", "<end>"}


class SonioxProvider(Provider):
    name = "soniox"
    streaming = True

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
        self.keyterms = keyterms or []

    def start(
        self,
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._on_partial = on_partial
        self._on_final = on_final
        self._final_text_parts: List[str] = []

        config = RealtimeSTTConfig(
            model=self.model,
            audio_format="pcm_s16le",
            num_channels=CHANNELS,
            sample_rate=SAMPLE_RATE,
            language_hints=[self.language] if self.language else None,
            context=StructuredContext(terms=self.keyterms) if self.keyterms else None,
        )
        client = SonioxClient(api_key=self.api_key)
        self._session = client.realtime.stt.connect(config=config)
        self._session.enter()

        self._listener_thread = threading.Thread(target=self._listen, daemon=True)
        self._listener_thread.start()

    def _listen(self) -> None:
        try:
            for event in self._session.receive_events():
                tokens = [t for t in event.tokens if t.text not in CONTROL_TOKENS]
                partial_text = "".join(t.text for t in tokens if not t.is_final)
                final_text = "".join(t.text for t in tokens if t.is_final)
                if final_text:
                    self._final_text_parts.append(final_text)
                    if self._on_final:
                        self._on_final(final_text)
                if partial_text and self._on_partial:
                    self._on_partial(partial_text)
                if event.finished:
                    break
        except Exception:
            # The socket may be force-closed by stop() below while this thread
            # is mid-read — that's expected once we're shutting down, not an error.
            pass

    def feed_audio(self, chunk: bytes) -> None:
        self._session.send_byte_chunk(chunk)

    def stop(self) -> str:
        self._session.finalize()
        self._listener_thread.join(timeout=5)
        if self._listener_thread.is_alive():
            # Listener didn't wrap up on its own — force the socket closed so
            # its blocking read unblocks, then give it a short grace period.
            self._session.close()
            self._listener_thread.join(timeout=2)
        else:
            self._session.close()
        return "".join(self._final_text_parts)
