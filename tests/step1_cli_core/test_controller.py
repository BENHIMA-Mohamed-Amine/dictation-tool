import pytest
from unittest.mock import MagicMock

import controller as controller_module
from controller import DictationController


class FakeConfig:
    def load(self):
        return {"selected_provider": "fake", "keyterms": ["term"]}

    def get_key(self, provider):
        return "fake-key"

    def provider_settings(self, provider):
        return {"model": None, "language": None}


@pytest.mark.parametrize("streaming", [False, True])
def test_record_once_drives_provider_in_order(monkeypatch, streaming):
    captured = {}

    class FakeProvider:
        def __init__(self):
            self.calls = []
            captured["instance"] = self

        def configure(self, api_key, model=None, language=None, keyterms=None):
            self.calls.append("configure")

        def start(self, on_partial=None, on_final=None):
            self.calls.append("start")

        def feed_audio(self, chunk):
            self.calls.append("feed_audio")

        def stop(self):
            self.calls.append("stop")
            return "final transcript"

    FakeProvider.streaming = streaming

    monkeypatch.setattr(controller_module, "PROVIDERS", {"fake": FakeProvider})
    monkeypatch.setattr("builtins.input", lambda *_: None)

    fake_recorder = MagicMock()
    fake_recorder.start.side_effect = lambda on_chunk: on_chunk(b"chunk")
    monkeypatch.setattr(controller_module, "AudioRecorder", lambda: fake_recorder)

    result = DictationController(config=FakeConfig()).record_once()

    assert result == "final transcript"
    assert captured["instance"].calls == ["configure", "start", "feed_audio", "stop"]
    fake_recorder.start.assert_called_once()
    fake_recorder.stop.assert_called_once()


def test_record_once_raises_without_api_key(monkeypatch):
    class FakeProvider:
        streaming = False

        def configure(self, **kwargs):
            pass

    monkeypatch.setattr(controller_module, "PROVIDERS", {"fake": FakeProvider})

    class NoKeyConfig(FakeConfig):
        def get_key(self, provider):
            return None

    with pytest.raises(RuntimeError):
        DictationController(config=NoKeyConfig()).record_once()
