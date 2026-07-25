import config as config_module
from config import ConfigStore


def test_unknown_provider_returns_defaults_not_keyerror(tmp_path):
    store = ConfigStore(config_dir=tmp_path)
    assert store.provider_settings("never-configured") == {"model": None, "language": None}


def test_round_trips_per_provider_settings(tmp_path):
    store = ConfigStore(config_dir=tmp_path)
    data = store.load()
    data["providers"]["groq"] = {"model": "whisper-large-v3", "language": "fr"}
    store.save(data)

    assert ConfigStore(config_dir=tmp_path).provider_settings("groq") == {
        "model": "whisper-large-v3",
        "language": "fr",
    }


def test_partial_entry_is_filled_in(tmp_path):
    # A provider block written before "language" existed must still load.
    store = ConfigStore(config_dir=tmp_path)
    data = store.load()
    data["providers"]["groq"] = {"model": "whisper-large-v3"}
    store.save(data)

    assert ConfigStore(config_dir=tmp_path).provider_settings("groq")["language"] is None


def test_has_key_reflects_keyring_without_exposing_value(tmp_path, monkeypatch):
    store = ConfigStore(config_dir=tmp_path)
    monkeypatch.setattr(config_module.keyring, "get_password", lambda *_: None)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert store.has_key("groq") is False

    monkeypatch.setattr(config_module.keyring, "get_password", lambda *_: "secret")
    assert store.has_key("groq") is True
