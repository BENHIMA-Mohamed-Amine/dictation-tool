import threading

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from config import ConfigStore
from controller import DictationController
from transcript_window import TranscriptWindow
from tray import TrayIcon


class App:
    def __init__(self) -> None:
        self.config = ConfigStore()
        self.controller = DictationController(config=self.config)
        self.transcript_window = TranscriptWindow(on_close=self._on_window_closed)
        self.tray = TrayIcon(config=self.config, on_toggle=self._on_toggle, on_quit=self._on_quit)
        # Every click spawns a worker thread; this lock makes sure a second
        # click waits for the previous start()/stop() to fully finish before
        # it even checks the recording state, instead of racing it.
        self._toggle_lock = threading.Lock()

    def _on_toggle(self) -> None:
        threading.Thread(target=self._toggle_worker, daemon=True).start()

    def _on_window_closed(self) -> None:
        # Closing the transcript window means "I'm done" — stop any active
        # recording too, via the same lock-protected path as a tray click.
        if self.controller.is_recording:
            self._on_toggle()

    def _toggle_worker(self) -> None:
        with self._toggle_lock:
            starting = not self.controller.is_recording
            try:
                if starting:
                    # controller.toggle() (start path) now returns as soon as
                    # the recorder is actually capturing — a provider's slow
                    # connect (e.g. Soniox's websocket handshake) happens in
                    # the background and no longer blocks this label flip.
                    GLib.idle_add(self.transcript_window.begin_new_segment)
                    self.controller.toggle(
                        on_partial=lambda text: GLib.idle_add(self.transcript_window.set_partial, text),
                        on_final=lambda text: GLib.idle_add(self.transcript_window.append_final, text),
                    )
                    GLib.idle_add(self.transcript_window.show_window)
                    GLib.idle_add(self.tray.set_recording, True)
                else:
                    # stop_async() only blocks for the fast part (recorder
                    # stop + is_recording flip) — the slow part (provider
                    # network teardown) finishes in the background, so this
                    # worker thread — and the _toggle_lock it holds — is
                    # released almost immediately. Holding the lock for the
                    # full stop() used to make a quick Start-after-Stop click
                    # queue up behind Soniox's multi-second session drain.
                    GLib.idle_add(self.tray.set_recording, False)
                    self.controller.stop_async()
            except Exception as exc:
                GLib.idle_add(self.tray.set_recording, False)
                GLib.idle_add(self.transcript_window.hide_window)
                print(f"Dictation error: {exc}")

    def _on_quit(self) -> None:
        Gtk.main_quit()

    def run(self) -> None:
        Gtk.main()


if __name__ == "__main__":
    App().run()
