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


def test_key_hint_shows_only_first_and_last_four(tmp_path, monkeypatch):
    store = ConfigStore(config_dir=tmp_path)
    monkeypatch.setattr(config_module.keyring, "get_password", lambda *_: "gsk_abcdefghijklmnop3f2a")

    hint = store.key_hint("groq")
    assert hint.startswith("gsk_")
    assert hint.endswith("3f2a")
    assert "abcdefghijklmnop" not in hint
    assert "•" in hint


def test_key_hint_fully_masks_short_keys(tmp_path, monkeypatch):
    # A first-4/last-4 preview of a 12-char key would expose most of it.
    store = ConfigStore(config_dir=tmp_path)
    monkeypatch.setattr(config_module.keyring, "get_password", lambda *_: "short-key-12")

    assert set(store.key_hint("groq")) == {"•"}


def test_key_hint_is_none_when_unset(tmp_path, monkeypatch):
    store = ConfigStore(config_dir=tmp_path)
    monkeypatch.setattr(config_module.keyring, "get_password", lambda *_: None)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    assert store.key_hint("groq") is None
