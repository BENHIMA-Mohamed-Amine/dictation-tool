import gi

gi.require_version("Gtk", "3.0")

from config import ConfigStore
from settings_window import SettingsWindow


def _window(tmp_path):
    return SettingsWindow(config=ConfigStore(config_dir=tmp_path))


def test_keyterms_add_dedupe_and_remove(tmp_path):
    window = _window(tmp_path)
    entry = window._keyterm_entry

    for term in ("kubernetes", "Anthropic", "kubernetes"):
        entry.set_text(term)
        entry.emit("activate")

    assert window._keyterms == ["kubernetes", "Anthropic"]
    assert entry.get_text() == ""

    window._remove_keyterm("kubernetes")
    assert window._keyterms == ["Anthropic"]


def test_blank_keyterm_is_ignored(tmp_path):
    window = _window(tmp_path)
    window._keyterm_entry.set_text("   ")
    window._keyterm_entry.emit("activate")
    assert window._keyterms == []


def test_save_persists_keyterms_and_provider_settings(tmp_path):
    window = _window(tmp_path)
    window._load_from_config()  # show_window() minus actually mapping a window

    window._keyterm_entry.set_text("Soniox")
    window._keyterm_entry.emit("activate")
    groq = window._tabs["groq"]
    groq._model_combo.set_active_id("whisper-large-v3")
    groq._language_combo.set_active_id("fr")

    window._on_save_clicked(None)

    reloaded = ConfigStore(config_dir=tmp_path)
    assert reloaded.load()["keyterms"] == ["Soniox"]
    assert reloaded.provider_settings("groq") == {
        "model": "whisper-large-v3",
        "language": "fr",
    }


def test_auto_detect_saves_as_none_not_empty_string(tmp_path):
    # The combo id for Auto-detect is "" (ComboBoxText ids must be strings);
    # it has to reach config.json as null or providers would send language="".
    window = _window(tmp_path)
    window._load_from_config()  # show_window() minus actually mapping a window
    window._tabs["groq"]._language_combo.set_active_id("")
    window._on_save_clicked(None)

    assert ConfigStore(config_dir=tmp_path).provider_settings("groq")["language"] is None


def test_provider_without_models_saves_none(tmp_path):
    window = _window(tmp_path)
    window._load_from_config()  # show_window() minus actually mapping a window
    assert window._tabs["nvidia"].values()["model"] is None


def test_cancel_discards_edits(tmp_path):
    window = _window(tmp_path)
    window._load_from_config()  # show_window() minus actually mapping a window
    window._keyterm_entry.set_text("throwaway")
    window._keyterm_entry.emit("activate")
    window._close()

    assert ConfigStore(config_dir=tmp_path).load()["keyterms"] == []


def test_reopening_reloads_from_disk(tmp_path):
    window = _window(tmp_path)
    window._load_from_config()  # show_window() minus actually mapping a window
    window._keyterm_entry.set_text("throwaway")
    window._keyterm_entry.emit("activate")
    window._close()

    window._load_from_config()  # show_window() minus actually mapping a window
    assert window._keyterms == []
