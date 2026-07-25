import threading
from typing import Callable, List, Optional

from audio import AudioRecorder
from config import ConfigStore
from providers import PROVIDERS


class _BufferedSink:
    """Buffers audio chunks until a real feed target is connected.

    Lets the mic start capturing the instant recording begins, instead of
    waiting on a provider's (possibly slow, network-bound) start() before
    audio can be fed anywhere — connecting later just flushes what piled up.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._target: Optional[Callable[[bytes], None]] = None
        self._buffered: List[bytes] = []

    def feed(self, chunk: bytes) -> None:
        with self._lock:
            if self._target is None:
                self._buffered.append(chunk)
                return
            target = self._target
        target(chunk)

    def connect(self, target: Callable[[bytes], None]) -> None:
        with self._lock:
            buffered, self._buffered = self._buffered, []
            self._target = target
        for chunk in buffered:
            target(chunk)


class DictationController:
    def __init__(self, config: Optional[ConfigStore] = None) -> None:
        self.config = config or ConfigStore()
        self._provider = None
        self._recorder = None
        self._recording = False
        self._session_id = 0
        self._connect_thread: Optional[threading.Thread] = None
        self._connect_error: Optional[Exception] = None

    def start(
        self,
        provider_name: Optional[str] = None,
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str], None]] = None,
    ) -> None:
        data = self.config.load()
        provider_name = provider_name or data["selected_provider"]

        provider_cls = PROVIDERS[provider_name]
        provider = provider_cls()

        api_key = self.config.get_key(provider_name)
        if not api_key:
            raise RuntimeError(f"No API key configured for provider '{provider_name}'")

        settings = self.config.provider_settings(provider_name)
        provider.configure(
            api_key=api_key,
            model=settings["model"],
            language=settings["language"],
            keyterms=data["keyterms"],
        )

        # A previous session's provider (e.g. Soniox's background listener
        # thread) can still be winding down and deliver a late callback after
        # this new session has already started. Tag each session so stale
        # callbacks from an old one are dropped instead of corrupting the
        # current transcript.
        self._session_id += 1
        session_id = self._session_id

        def guarded_partial(text: str) -> None:
            if session_id == self._session_id and on_partial:
                on_partial(text)

        def guarded_final(text: str) -> None:
            if session_id == self._session_id and on_final:
                on_final(text)

        # Start capturing mic audio immediately, buffering chunks into `sink`
        # rather than waiting for provider.start() — for streaming providers
        # (e.g. Soniox's websocket handshake) that connect can take the
        # better part of a second, and gating mic capture behind it means
        # losing the first bit of speech.
        sink = _BufferedSink()
        recorder = AudioRecorder()
        recorder.start(on_chunk=sink.feed)

        self._connect_error = None

        def connect_provider() -> None:
            try:
                provider.start(on_partial=guarded_partial, on_final=guarded_final)
            except Exception as exc:
                self._connect_error = exc
                return
            sink.connect(provider.feed_audio)

        connect_thread = threading.Thread(target=connect_provider, daemon=True)
        connect_thread.start()

        self._provider = provider
        self._recorder = recorder
        self._connect_thread = connect_thread
        self._recording = True

    @property
    def is_recording(self) -> bool:
        return self._recording

    def _prepare_stop(self):
        # Capture everything the slow teardown below needs as locals *before*
        # flipping is_recording — once flipped, a new start() can legally run
        # concurrently (e.g. from stop_async()'s background thread) and will
        # overwrite self._provider/_recorder/_connect_error for the *next*
        # session. Reading through self. after this point would risk tearing
        # down the wrong session.
        connect_thread = self._connect_thread
        recorder = self._recorder
        provider = self._provider

        # Providers can't be stopped before they finished connecting (e.g.
        # Soniox needs its session to exist) — this wait is invisible to the
        # user since the tray label already flipped on click.
        connect_thread.join()
        connect_error = self._connect_error
        recorder.stop()
        self._recording = False
        return provider, connect_error

    def stop(self) -> str:
        provider, connect_error = self._prepare_stop()
        if connect_error is not None:
            raise connect_error
        return provider.stop()

    def stop_async(self) -> None:
        """Same effect as stop(), but only the fast part (recorder stop +
        is_recording flip) runs before returning — the slow part (provider
        network teardown, e.g. Soniox's multi-second session drain) finishes
        in a background thread.

        Used by the tray/hotkey path so a quick Start click right after Stop
        doesn't queue up behind that slow teardown. The CLI path uses the
        synchronous stop() instead, since it needs the returned transcript.
        """
        provider, connect_error = self._prepare_stop()

        def finish() -> None:
            try:
                if connect_error is not None:
                    raise connect_error
                provider.stop()
            except Exception as exc:
                print(f"Dictation error: {exc}")

        threading.Thread(target=finish, daemon=True).start()

    def toggle(
        self,
        provider_name: Optional[str] = None,
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str], None]] = None,
    ) -> Optional[str]:
        if not self._recording:
            self.start(provider_name, on_partial=on_partial, on_final=on_final)
            return None
        return self.stop()

    def record_once(self, provider_name: Optional[str] = None) -> str:
        self.start(
            provider_name,
            on_partial=print,
            on_final=lambda text: print(f"[final] {text}"),
        )
        input("Recording... press Enter to stop.\n")
        return self.stop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dictation CLI")
    parser.add_argument("--provider", choices=list(PROVIDERS), default=None)
    args = parser.parse_args()

    text = DictationController().record_once(provider_name=args.provider)
    print("\nTranscript:\n" + text)
