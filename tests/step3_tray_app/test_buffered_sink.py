import threading
import time
from unittest.mock import MagicMock

import controller as controller_module
from controller import DictationController, _BufferedSink


def test_feed_before_connect_is_buffered_then_flushed_in_order():
    sink = _BufferedSink()
    received = []

    sink.feed(b"a")
    sink.feed(b"b")
    assert received == []  # nothing delivered yet, no target connected

    sink.connect(received.append)
    assert received == [b"a", b"b"]


def test_feed_after_connect_goes_straight_to_target():
    sink = _BufferedSink()
    received = []
    sink.connect(received.append)

    sink.feed(b"c")

    assert received == [b"c"]


class SlowConnectProvider:
    streaming = True

    def __init__(self):
        self.calls = []

    def configure(self, api_key, model=None, language=None, keyterms=None):
        self.calls.append("configure")

    def start(self, on_partial=None, on_final=None):
        time.sleep(0.2)  # simulates a slow websocket handshake
        self.calls.append("start")

    def feed_audio(self, chunk):
        self.calls.append(("feed_audio", chunk))

    def stop(self):
        self.calls.append("stop")
        return "text"


class FakeConfig:
    def load(self):
        return {"selected_provider": "fake", "keyterms": []}

    def get_key(self, provider):
        return "fake-key"


def test_start_returns_before_slow_provider_connects_but_stop_waits_for_it(monkeypatch):
    monkeypatch.setattr(controller_module, "PROVIDERS", {"fake": SlowConnectProvider})

    fake_recorder = MagicMock()
    chunks_fed_immediately = []
    fake_recorder.start.side_effect = lambda on_chunk: chunks_fed_immediately.append(on_chunk)
    monkeypatch.setattr(controller_module, "AudioRecorder", lambda: fake_recorder)

    controller = DictationController(config=FakeConfig())

    t0 = time.perf_counter()
    controller.start()
    elapsed = time.perf_counter() - t0

    # start() must not block on the provider's 0.2s connect delay.
    assert elapsed < 0.1

    # Feed a chunk while the provider is still connecting — must not error,
    # must be buffered rather than dropped.
    on_chunk = chunks_fed_immediately[0]
    on_chunk(b"chunk-during-connect")

    provider = controller._provider
    assert "start" not in provider.calls  # still connecting

    text = controller.stop()

    assert text == "text"
    assert provider.calls[0] == "configure"
    assert "start" in provider.calls
    assert ("feed_audio", b"chunk-during-connect") in provider.calls
    assert provider.calls[-1] == "stop"
    assert provider.calls.index("start") < provider.calls.index(("feed_audio", b"chunk-during-connect"))
