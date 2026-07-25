import controller as controller_module
from controller import DictationController


class RecordingProvider:
    streaming = False

    def __init__(self):
        self.configured = None

    def configure(self, api_key, model=None, language=None, keyterms=None):
        self.configured = {"model": model, "language": language, "keyterms": keyterms}

    def start(self, on_partial=None, on_final=None):
        pass

    def feed_audio(self, chunk):
        pass

    def stop(self):
        return ""


class FakeConfig:
    def __init__(self, settings):
        self._settings = settings

    def load(self):
        return {"selected_provider": "fake", "keyterms": ["term"]}

    def get_key(self, provider):
        return "fake-key"

    def provider_settings(self, provider):
        return self._settings


def _start_with(monkeypatch, settings):
    provider = RecordingProvider()
    monkeypatch.setitem(controller_module.PROVIDERS, "fake", lambda: provider)
    monkeypatch.setattr(controller_module, "AudioRecorder", lambda: _NoopRecorder())
    ctrl = DictationController(config=FakeConfig(settings))
    ctrl.start()
    ctrl.stop()
    return provider.configured


class _NoopRecorder:
    def start(self, on_chunk):
        pass

    def stop(self):
        pass


def test_configured_model_and_language_reach_the_provider(monkeypatch):
    configured = _start_with(monkeypatch, {"model": "whisper-large-v3", "language": "fr"})
    assert configured["model"] == "whisper-large-v3"
    assert configured["language"] == "fr"
    assert configured["keyterms"] == ["term"]


def test_auto_language_arrives_as_none(monkeypatch):
    # Auto-detect is None all the way down — providers read that as "send no
    # language hint", so it must not be coerced to "" or a default code.
    configured = _start_with(monkeypatch, {"model": None, "language": None})
    assert configured["language"] is None
    assert configured["model"] is None
