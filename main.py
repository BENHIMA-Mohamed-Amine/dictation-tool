import socket
import threading
from pathlib import Path

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from config import CONFIG_DIR, ConfigStore
from controller import DictationController
from settings_window import SettingsWindow
from transcript_window import TranscriptWindow
from tray import TrayIcon

SOCKET_PATH = CONFIG_DIR / "ctl.sock"


class ControlSocket:
    """Unix socket letting an external process (e.g. a GNOME keyboard
    shortcut running dictation_ctl.py) trigger start/stop/quit in this
    running app. Wayland blocks apps from registering their own global
    hotkeys, so the actual key binding lives outside this app entirely —
    this socket is just the app's side of that handoff.
    """

    def __init__(self, on_start, on_stop, on_quit, socket_path: Path = SOCKET_PATH) -> None:
        self._handlers = {b"start": on_start, b"stop": on_stop, b"quit": on_quit}
        self._socket_path = socket_path

        self._socket_path.parent.mkdir(parents=True, exist_ok=True)
        # A stale socket file left over from a previous crashed run makes
        # bind() fail with "address already in use" otherwise.
        self._socket_path.unlink(missing_ok=True)

        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(str(self._socket_path))
        self._server.listen(1)

    def start(self) -> None:
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self) -> None:
        while True:
            try:
                conn, _ = self._server.accept()
            except OSError:
                return  # socket closed underneath us
            with conn:
                data = conn.recv(64)
            handler = self._handlers.get(data)
            if handler:
                GLib.idle_add(handler)

    def close(self) -> None:
        self._server.close()
        self._socket_path.unlink(missing_ok=True)


class App:
    def __init__(self) -> None:
        self.config = ConfigStore()
        self.controller = DictationController(config=self.config)
        self.transcript_window = TranscriptWindow(
            on_close=self._on_window_closed, on_toggle=self._on_toggle
        )
        self.settings_window = SettingsWindow(config=self.config)
        self.tray = TrayIcon(
            config=self.config,
            on_toggle=self._on_toggle,
            on_quit=self._on_quit,
            on_settings=self.settings_window.show_window,
        )
        # Every click spawns a worker thread; this lock makes sure a second
        # click waits for the previous start()/stop() to fully finish before
        # it even checks the recording state, instead of racing it.
        self._toggle_lock = threading.Lock()
        self.control_socket = ControlSocket(
            on_start=self._on_hotkey_start,
            on_stop=self._on_hotkey_stop,
            on_quit=self._on_quit,
        )
        self.control_socket.start()

    def _on_toggle(self) -> None:
        threading.Thread(target=self._toggle_worker, daemon=True).start()

    def _set_recording(self, recording: bool) -> None:
        # Both surfaces show the same state; the window button is the one you
        # can click twice in a row without the tray menu closing on you.
        self.tray.set_recording(recording)
        self.transcript_window.set_recording(recording)

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
                    GLib.idle_add(self._set_recording, True)
                else:
                    # stop_async() only blocks for the fast part (recorder
                    # stop + is_recording flip) — the slow part (provider
                    # network teardown) finishes in the background, so this
                    # worker thread — and the _toggle_lock it holds — is
                    # released almost immediately. Holding the lock for the
                    # full stop() used to make a quick Start-after-Stop click
                    # queue up behind Soniox's multi-second session drain.
                    GLib.idle_add(self._set_recording, False)
                    self.controller.stop_async()
            except Exception as exc:
                GLib.idle_add(self._set_recording, False)
                GLib.idle_add(self.transcript_window.hide_window)
                print(f"Dictation error: {exc}")

    def _on_hotkey_start(self) -> None:
        if self.controller.is_recording:
            GLib.idle_add(self.transcript_window.raise_window)
        else:
            self._on_toggle()

    def _on_hotkey_stop(self) -> None:
        if self.controller.is_recording:
            self._on_toggle()

    def _on_quit(self) -> None:
        if self.controller.is_recording:
            # Blocking here (rather than stop_async) is deliberate: the
            # process is about to exit, so this is the last chance to let
            # the provider tear down cleanly (e.g. Soniox's session drain)
            # instead of the connection just dying mid-stream.
            try:
                self.controller.stop()
            except Exception as exc:
                print(f"Dictation error: {exc}")
        self.control_socket.close()
        Gtk.main_quit()

    def run(self) -> None:
        self.transcript_window.show_window()
        Gtk.main()


if __name__ == "__main__":
    App().run()
