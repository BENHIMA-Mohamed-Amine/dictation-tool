import time

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")
from gi.repository import AyatanaAppIndicator3 as AppIndicator3
from gi.repository import Gtk

from config import ConfigStore
from providers import PROVIDERS

# AppIndicator/dbusmenu is known to occasionally emit "activate" twice for a
# single click. Without a debounce, that fires toggle() twice in a row —
# stop, then immediately start again — which looks like the label flickering
# back to "Stop recording" right after it flips to "Start recording".
TOGGLE_DEBOUNCE_SECONDS = 0.15


class TrayIcon:
    def __init__(self, config: ConfigStore, on_toggle, on_quit) -> None:
        self.config = config
        self.on_toggle = on_toggle
        self.on_quit = on_quit
        self._last_toggle_time = 0.0

        self.indicator = AppIndicator3.Indicator.new(
            "dictation-tool",
            "audio-input-microphone-symbolic",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        self.menu = Gtk.Menu()

        self.toggle_item = Gtk.MenuItem(label="Start recording")
        self.toggle_item.connect("activate", self._on_toggle_clicked)
        self.menu.append(self.toggle_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        provider_item = Gtk.MenuItem(label="Provider")
        provider_submenu = Gtk.Menu()
        selected_provider = self.config.load()["selected_provider"]
        group = None
        for name in PROVIDERS:
            item = Gtk.RadioMenuItem.new_with_label_from_widget(group, name)
            group = item
            item.set_active(name == selected_provider)
            item.connect("toggled", self._on_provider_toggled, name)
            provider_submenu.append(item)
        provider_item.set_submenu(provider_submenu)
        self.menu.append(provider_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _widget: self.on_quit())
        self.menu.append(quit_item)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

    def set_recording(self, recording: bool) -> None:
        # Mutating the existing item's label in place (set_label) doesn't
        # reliably re-render through the dbusmenu proxy GNOME Shell uses for
        # AppIndicator menus (observed on Wayland) — the backing state
        # changes but the displayed label sticks at its old value. Rebuilding
        # the item and re-registering the whole menu forces a real refresh.
        label = "Stop recording" if recording else "Start recording"
        self.menu.remove(self.toggle_item)
        self.toggle_item = Gtk.MenuItem(label=label)
        self.toggle_item.connect("activate", self._on_toggle_clicked)
        self.menu.insert(self.toggle_item, 0)
        self.menu.show_all()
        self.indicator.set_menu(self.menu)

    def _on_toggle_clicked(self, _widget) -> None:
        # Label state is decided by App/_toggle_worker (single source of
        # truth) once it actually processes this click, not here.
        now = time.monotonic()
        if now - self._last_toggle_time < TOGGLE_DEBOUNCE_SECONDS:
            return
        self._last_toggle_time = now
        self.on_toggle()

    def _on_provider_toggled(self, widget, name: str) -> None:
        if widget.get_active():
            data = self.config.load()
            data["selected_provider"] = name
            self.config.save(data)
