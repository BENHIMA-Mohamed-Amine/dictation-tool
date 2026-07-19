from unittest.mock import MagicMock

import controller as controller_module
from controller import DictationController


class FakeConfig:
    def load(self):
        return {"selected_provider": "fake", "keyterms": []}

    def get_key(self, provider):
        return "fake-key"


class FakeProvider:
    streaming = False

    def __init__(self):
        self.calls = []

    def configure(self, api_key, model=None, language=None, keyterms=None):
        self.calls.append("configure")

    def start(self, on_partial=None, on_final=None):
        self.calls.append("start")

    def feed_audio(self, chunk):
        self.calls.append("feed_audio")

    def stop(self):
        self.calls.append("stop")
        return "final transcript"


def test_toggle_starts_then_stops(monkeypatch):
    captured = {}

    class TrackedFakeProvider(FakeProvider):
        def __init__(self):
            super().__init__()
            captured["instance"] = self

    monkeypatch.setattr(controller_module, "PROVIDERS", {"fake": TrackedFakeProvider})

    fake_recorder = MagicMock()
    fake_recorder.start.side_effect = lambda on_chunk: on_chunk(b"chunk")
    monkeypatch.setattr(controller_module, "AudioRecorder", lambda: fake_recorder)

    controller = DictationController(config=FakeConfig())

    first_result = controller.toggle()
    assert first_result is None
    controller._connect_thread.join()
    assert captured["instance"].calls == ["configure", "start", "feed_audio"]
    fake_recorder.stop.assert_not_called()

    second_result = controller.toggle()
    assert second_result == "final transcript"
    assert captured["instance"].calls == ["configure", "start", "feed_audio", "stop"]
    fake_recorder.stop.assert_called_once()


class CallbackCapturingProvider:
    streaming = True
    instances = []

    def __init__(self):
        self.calls = []
        self.on_partial = None
        self.on_final = None
        CallbackCapturingProvider.instances.append(self)

    def configure(self, api_key, model=None, language=None, keyterms=None):
        self.calls.append("configure")

    def start(self, on_partial=None, on_final=None):
        self.on_partial = on_partial
        self.on_final = on_final
        self.calls.append("start")

    def feed_audio(self, chunk):
        self.calls.append("feed_audio")

    def stop(self):
        self.calls.append("stop")
        return "session text"


def test_stale_callbacks_from_previous_session_are_ignored(monkeypatch):
    CallbackCapturingProvider.instances = []
    monkeypatch.setattr(controller_module, "PROVIDERS", {"fake": CallbackCapturingProvider})
    monkeypatch.setattr(controller_module, "AudioRecorder", lambda: MagicMock())

    controller = DictationController(config=FakeConfig())

    received_1 = []
    controller.start(on_partial=received_1.append, on_final=received_1.append)
    session1_provider = CallbackCapturingProvider.instances[0]
    controller.stop()

    received_2 = []
    controller.start(on_partial=received_2.append, on_final=received_2.append)

    # Simulate session 1's listener thread delivering a late event after
    # session 2 has already started.
    session1_provider.on_partial("stale partial")
    session1_provider.on_final("stale final")

    assert received_2 == []


def test_record_once_still_works_after_refactor(monkeypatch):
    monkeypatch.setattr(controller_module, "PROVIDERS", {"fake": FakeProvider})
    monkeypatch.setattr("builtins.input", lambda *_: None)

    fake_recorder = MagicMock()
    fake_recorder.start.side_effect = lambda on_chunk: on_chunk(b"chunk")
    monkeypatch.setattr(controller_module, "AudioRecorder", lambda: fake_recorder)

    result = DictationController(config=FakeConfig()).record_once()

    assert result == "final transcript"
