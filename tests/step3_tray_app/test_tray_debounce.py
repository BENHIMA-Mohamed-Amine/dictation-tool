import time

from config import ConfigStore
from tray import TrayIcon


class FakeConfig(ConfigStore):
    def __init__(self):
        pass

    def load(self):
        return {"selected_provider": "groq", "keyterms": []}


def make_tray(on_toggle):
    return TrayIcon(config=FakeConfig(), on_toggle=on_toggle, on_quit=lambda: None)


def test_rapid_double_activate_only_toggles_once():
    calls = []
    tray = make_tray(lambda: calls.append(1))

    # Simulates the known AppIndicator/dbusmenu quirk where a single click
    # delivers two "activate" signals back to back.
    tray._on_toggle_clicked(None)
    tray._on_toggle_clicked(None)

    assert calls == [1]


def test_separate_clicks_each_toggle():
    calls = []
    tray = make_tray(lambda: calls.append(1))

    tray._on_toggle_clicked(None)
    tray._last_toggle_time -= 1  # simulate enough real time passing
    tray._on_toggle_clicked(None)

    assert calls == [1, 1]


def test_set_recording_updates_label_and_rebuilt_item_still_toggles():
    calls = []
    tray = make_tray(lambda: calls.append(1))

    tray.set_recording(True)
    assert tray.toggle_item.get_label() == "Stop recording"

    # set_recording rebuilds the menu item (dbusmenu label-refresh
    # workaround) — confirm the fresh item is still wired to on_toggle.
    tray.toggle_item.activate()
    assert calls == [1]

    tray._last_toggle_time -= 1
    tray.set_recording(False)
    assert tray.toggle_item.get_label() == "Start recording"
