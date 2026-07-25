import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk

from config import ConfigStore
from providers import PROVIDERS

# Keyterms render as pills per design/settings_window.svg. Colours come from
# the GTK theme (@theme_selected_* ) rather than the mockup's hardcoded blues,
# so the window still looks right in a dark theme.
CHIP_CSS = b"""
.keyterm-chip {
  background-color: alpha(@theme_selected_bg_color, 0.25);
  border-radius: 10px;
  padding: 2px 4px 2px 10px;
}
.keyterm-chip button {
  padding: 0 4px;
  min-width: 0;
  min-height: 0;
}
"""


class SettingsWindow(Gtk.Window):
    """Global keyterms + per-provider model/key/language.

    Provider tabs are built by iterating PROVIDERS and reading each class's
    MODELS/LANGUAGES, so a new provider shows up here with no changes to this
    file.

    Edits are held in memory and only written on Save — except API keys, which
    go straight to the keyring from their own dialog (a secret shouldn't sit in
    a widget waiting for a Save that may never come, and Cancel un-saving a key
    you just pasted would be a nasty surprise).
    """

    def __init__(self, config: ConfigStore) -> None:
        super().__init__(title="Dictation tool settings")
        self.config = config
        self.set_default_size(480, 520)
        self._keyterms: list[str] = []
        self._tabs: dict[str, _ProviderTab] = {}

        provider = Gtk.CssProvider()
        provider.load_from_data(CHIP_CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_border_width(12)
        self.add(box)

        box.pack_start(_label("Keyterms / vocabulary boost (applies to all providers)"), False, False, 0)

        self._chips = Gtk.FlowBox()
        self._chips.set_selection_mode(Gtk.SelectionMode.NONE)
        self._chips.set_max_children_per_line(6)
        box.pack_start(self._chips, False, False, 0)

        self._keyterm_entry = Gtk.Entry()
        self._keyterm_entry.set_placeholder_text("Type a term, press Enter to add — then Save")
        self._keyterm_entry.connect("activate", self._on_keyterm_entered)
        box.pack_start(self._keyterm_entry, False, False, 0)

        notebook = Gtk.Notebook()
        notebook.set_vexpand(True)
        box.pack_start(notebook, True, True, 0)
        for name, provider_cls in PROVIDERS.items():
            tab = _ProviderTab(name, provider_cls, config, parent=self)
            self._tabs[name] = tab
            notebook.append_page(tab, Gtk.Label(label=provider_cls.display_name))

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        footer.set_halign(Gtk.Align.END)
        box.pack_start(footer, False, False, 0)

        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda _b: self._close())
        footer.pack_start(cancel, False, False, 0)

        save = Gtk.Button(label="Save")
        save.get_style_context().add_class("suggested-action")
        save.connect("clicked", self._on_save_clicked)
        footer.pack_start(save, False, False, 0)

        self.connect("delete-event", lambda *_: self._close())

    def show_window(self) -> None:
        # Reload every time so the window can't show state that drifted from
        # disk (e.g. the provider changed from the tray since it was last open).
        self._load_from_config()
        self.show_all()
        self.present()

    def _close(self) -> bool:
        self.hide()
        return True

    def _load_from_config(self) -> None:
        data = self.config.load()
        self._keyterms = list(data["keyterms"])
        self._render_chips()
        for name, tab in self._tabs.items():
            tab.load(self.config.provider_settings(name))

    def _on_save_clicked(self, _button) -> None:
        data = self.config.load()
        data["keyterms"] = list(self._keyterms)
        data["providers"] = {name: tab.values() for name, tab in self._tabs.items()}
        self.config.save(data)
        self._close()

    def _on_keyterm_entered(self, entry) -> None:
        term = entry.get_text().strip()
        if term and term not in self._keyterms:
            self._keyterms.append(term)
            self._render_chips()
        entry.set_text("")

    def _remove_keyterm(self, term: str) -> None:
        self._keyterms.remove(term)
        self._render_chips()

    def _render_chips(self) -> None:
        for child in self._chips.get_children():
            self._chips.remove(child)
        for term in self._keyterms:
            chip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            chip.get_style_context().add_class("keyterm-chip")
            # FlowBox gives every child an equal-width column; without this the
            # pill background stretches across it instead of hugging the word.
            chip.set_halign(Gtk.Align.START)
            chip.pack_start(Gtk.Label(label=term), False, False, 0)
            remove = Gtk.Button(label="×")
            remove.set_relief(Gtk.ReliefStyle.NONE)
            remove.set_tooltip_text(f"Remove “{term}”")
            remove.connect("clicked", lambda _b, t=term: self._remove_keyterm(t))
            chip.pack_start(remove, False, False, 0)
            self._chips.add(chip)
        self._chips.show_all()


class _ProviderTab(Gtk.Box):
    def __init__(self, name: str, provider_cls, config: ConfigStore, parent: Gtk.Window) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(12)
        self.name = name
        self.display_name = provider_cls.display_name
        self.config = config
        self.parent_window = parent

        self.pack_start(_label("Model"), False, False, 0)
        self.pack_start(Gtk.Label(label=provider_cls.MODEL_LABEL, xalign=0), False, False, 0)

        self.pack_start(_label("API key"), False, False, 0)
        key_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._key_status = Gtk.Label(xalign=0)
        key_row.pack_start(self._key_status, True, True, 0)
        change = Gtk.Button(label="Change")
        change.connect("clicked", self._on_change_key_clicked)
        key_row.pack_start(change, False, False, 0)
        self.pack_start(key_row, False, False, 0)

        self._language_combo = Gtk.ComboBoxText()
        # id "" stands in for None — ComboBoxText ids must be strings, and the
        # mapping back to None happens in values().
        for label, code in provider_cls.LANGUAGES:
            self._language_combo.append(code or "", label)
        self.pack_start(_label("Language"), False, False, 0)
        self.pack_start(self._language_combo, False, False, 0)

        self._refresh_key_status()

    def load(self, settings: dict) -> None:
        self._language_combo.set_active_id(settings["language"] or "")
        if self._language_combo.get_active_id() is None:
            self._language_combo.set_active(0)
        self._refresh_key_status()

    def values(self) -> dict:
        # model stays None: each provider has exactly one model, and which one
        # that is lives in the provider module. The field is kept so a provider
        # that gains a choice has somewhere to store it.
        language = self._language_combo.get_active_id()
        return {"model": None, "language": language or None}

    def _refresh_key_status(self) -> None:
        hint = self.config.key_hint(self.name)
        self._key_status.set_text(hint or "Not set")

    def _on_change_key_clicked(self, _button) -> None:
        dialog = Gtk.Dialog(title=f"{self.display_name} API key", transient_for=self.parent_window, modal=True)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
        entry = Gtk.Entry()
        entry.set_visibility(False)  # never render the secret in plaintext
        entry.set_placeholder_text("Paste API key")
        entry.set_activates_default(True)
        dialog.set_default_response(Gtk.ResponseType.OK)
        content = dialog.get_content_area()
        content.set_border_width(12)
        content.set_spacing(6)
        content.add(entry)
        dialog.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            value = entry.get_text().strip()
            if value:
                # Straight to the keyring — the value is never stored on this
                # widget or in config.json.
                self.config.set_key(self.name, value)
                self._refresh_key_status()
        dialog.destroy()


def _label(text: str) -> Gtk.Label:
    label = Gtk.Label(label=text, xalign=0)
    label.get_style_context().add_class("dim-label")
    return label
