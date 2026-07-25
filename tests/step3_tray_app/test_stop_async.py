import time
from unittest.mock import MagicMock

import controller as controller_module
from controller import DictationController


class FakeConfig:
    def load(self):
        return {"selected_provider": "fake", "keyterms": []}

    def get_key(self, provider):
        return "fake-key"

    def provider_settings(self, provider):
        return {"model": None, "language": None}


class SlowStopProvider:
    streaming = False
    instances = []

    def __init__(self):
        self.calls = []
        SlowStopProvider.instances.append(self)

    def configure(self, api_key, model=None, language=None, keyterms=None):
        self.calls.append("configure")

    def start(self, on_partial=None, on_final=None):
        self.calls.append("start")

    def feed_audio(self, chunk):
        self.calls.append("feed_audio")

    def stop(self):
        time.sleep(0.3)  # simulates Soniox's multi-second session drain
        self.calls.append("stop")
        return f"text from {id(self)}"


def make_controller(monkeypatch):
    monkeypatch.setattr(controller_module, "PROVIDERS", {"fake": SlowStopProvider})
    monkeypatch.setattr(controller_module, "AudioRecorder", lambda: MagicMock())
    return DictationController(config=FakeConfig())


def test_stop_async_returns_before_slow_provider_stop_completes(monkeypatch):
    SlowStopProvider.instances = []
    controller = make_controller(monkeypatch)

    controller.start()
    controller._connect_thread.join()

    t0 = time.perf_counter()
    controller.stop_async()
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.1  # must not block on the 0.3s provider.stop()
    assert controller.is_recording is False  # flipped immediately


def test_second_start_during_first_stop_teardown_does_not_corrupt_state(monkeypatch):
    SlowStopProvider.instances = []
    controller = make_controller(monkeypatch)

    controller.start()
    controller._connect_thread.join()
    session1_provider = SlowStopProvider.instances[0]

    controller.stop_async()  # session 1's slow stop() is now running in the background
    assert controller.is_recording is False

    # Immediately start a second session, before session 1's background
    # finish() has completed its 0.3s sleep.
    controller.start()
    controller._connect_thread.join()
    session2_provider = SlowStopProvider.instances[1]
    assert session2_provider is not session1_provider

    time.sleep(0.5)  # let session 1's background finish() complete

    assert "stop" in session1_provider.calls
    assert "stop" not in session2_provider.calls  # session 2 still recording
