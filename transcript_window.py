import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk


class TranscriptWindow(Gtk.Window):
    def __init__(self, on_close=None) -> None:
        super().__init__(title="Dictation transcript")
        self._on_close = on_close
        self.set_default_size(420, 220)
        self.set_keep_above(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(8)
        self.add(box)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        box.pack_start(scroller, True, True, 0)

        self._text_view = Gtk.TextView()
        self._text_view.set_editable(False)
        self._text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self._buffer = self._text_view.get_buffer()
        scroller.add(self._text_view)

        copy_button = Gtk.Button(label="Copy")
        copy_button.connect("clicked", self._on_copy_clicked)
        box.pack_start(copy_button, False, False, 0)

        self.connect("delete-event", self._on_delete_event)

        self._final_text = ""

    def _on_delete_event(self, _widget, _event) -> bool:
        # Hide instead of letting GTK destroy the window on close (X button) —
        # this widget is reused across recordings, not recreated each time.
        self.hide_window()
        self.reset()
        if self._on_close:
            self._on_close()
        return True

    def show_window(self) -> None:
        self.show_all()

    def hide_window(self) -> None:
        self.hide()

    def reset(self) -> None:
        self._final_text = ""
        self._buffer.set_text("")

    def begin_new_segment(self) -> None:
        # Called when a new recording starts, so consecutive recordings are
        # visually separated instead of run together or wiping each other.
        if self._final_text and not self._final_text.endswith("\n"):
            self._final_text += "\n"

    def set_partial(self, text: str) -> None:
        self._buffer.set_text(self._final_text + text)
        self._scroll_to_end()

    def append_final(self, text: str) -> None:
        self._final_text += text
        self._buffer.set_text(self._final_text)
        self._scroll_to_end()

    def _scroll_to_end(self) -> None:
        self._text_view.scroll_to_iter(self._buffer.get_end_iter(), 0.0, False, 0.0, 0.0)

    def _on_copy_clicked(self, _button) -> None:
        start, end = self._buffer.get_bounds()
        text = self._buffer.get_text(start, end, False)
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()
