import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk


class TranscriptWindow(Gtk.Window):
    def __init__(self, on_close=None, on_toggle=None) -> None:
        super().__init__(title="Dictation transcript")
        self._on_close = on_close
        self._on_toggle = on_toggle
        self.set_default_size(420, 220)
        self.set_keep_above(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(8)
        self.add(box)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        box.pack_start(scroller, True, True, 0)

        self._text_view = Gtk.TextView()
        self._text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self._buffer = self._text_view.get_buffer()
        scroller.add(self._text_view)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.pack_start(buttons, False, False, 0)

        self._toggle_button = Gtk.Button(label="Start recording")
        self._toggle_button.connect("clicked", lambda _b: self._on_toggle and self._on_toggle())
        buttons.pack_start(self._toggle_button, True, True, 0)

        copy_button = Gtk.Button(label="Copy")
        copy_button.connect("clicked", self._on_copy_clicked)
        buttons.pack_start(copy_button, True, True, 0)

        clear_button = Gtk.Button(label="Clear")
        clear_button.connect("clicked", lambda _b: self.reset())
        buttons.pack_start(clear_button, True, True, 0)

        self.connect("delete-event", self._on_delete_event)

        # Everything before this mark is settled text the user owns and may
        # have edited; everything after it is the in-flight partial we're free
        # to replace. Rewriting the whole buffer instead (the old approach)
        # meant every partial reverted the user's edits.
        self._partial_start = self._buffer.create_mark(
            None, self._buffer.get_end_iter(), True
        )

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
        self.present()

    def raise_window(self) -> None:
        """Bring an already-visible-but-buried window to the front.

        On Wayland, present() on a window that's already mapped is blocked
        by GNOME's focus-stealing prevention — only a genuinely new window
        map reliably gets focus granted. Unmapping and remapping on the next
        loop iteration gets treated as one, which does get focus.
        """
        self.hide()
        GLib.idle_add(self.show_window)

    def hide_window(self) -> None:
        self.hide()

    def set_recording(self, recording: bool) -> None:
        self._toggle_button.set_label("Stop recording" if recording else "Start recording")

    def reset(self) -> None:
        self._buffer.set_text("")
        self._settle()

    def begin_new_segment(self) -> None:
        # Called when a new recording starts, so consecutive recordings are
        # visually separated instead of run together or wiping each other.
        self._drop_partial()
        text = self._buffer_text()
        if text and not text.endswith("\n"):
            self._buffer.insert(self._buffer.get_end_iter(), "\n")
        self._settle()

    def set_partial(self, text: str) -> None:
        self._drop_partial()
        self._buffer.insert(self._buffer.get_end_iter(), text)
        self._scroll_to_end()

    def append_final(self, text: str) -> None:
        self._drop_partial()
        self._buffer.insert(self._buffer.get_end_iter(), text)
        self._settle()
        self._scroll_to_end()

    def _drop_partial(self) -> None:
        self._buffer.delete(
            self._buffer.get_iter_at_mark(self._partial_start),
            self._buffer.get_end_iter(),
        )

    def _settle(self) -> None:
        self._buffer.move_mark(self._partial_start, self._buffer.get_end_iter())

    def _scroll_to_end(self) -> None:
        self._text_view.scroll_to_iter(self._buffer.get_end_iter(), 0.0, False, 0.0, 0.0)

    def _buffer_text(self) -> str:
        start, end = self._buffer.get_bounds()
        return self._buffer.get_text(start, end, False)

    def _on_copy_clicked(self, _button) -> None:
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(self._buffer_text(), -1)
        clipboard.store()
