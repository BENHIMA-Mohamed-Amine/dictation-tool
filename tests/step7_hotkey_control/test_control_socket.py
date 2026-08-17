import socket
import time

from gi.repository import GLib

from main import ControlSocket


def _pump():
    # idle_add callbacks only run once the main loop iterates; there's no
    # Gtk.main() here, so iterate the default context manually.
    time.sleep(0.05)
    ctx = GLib.MainContext.default()
    while ctx.iteration(False):
        pass


def _send(socket_path, data: bytes) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(str(socket_path))
        sock.sendall(data)


def test_dispatches_start_stop_quit_to_the_right_handler(tmp_path):
    calls = []
    ctl = ControlSocket(
        on_start=lambda: calls.append("start"),
        on_stop=lambda: calls.append("stop"),
        on_quit=lambda: calls.append("quit"),
        socket_path=tmp_path / "ctl.sock",
    )
    ctl.start()
    try:
        for action in ("start", "stop", "quit"):
            _send(ctl._socket_path, action.encode())
            _pump()
        assert calls == ["start", "stop", "quit"]
    finally:
        ctl.close()


def test_unrecognized_message_is_ignored(tmp_path):
    calls = []
    ctl = ControlSocket(
        on_start=lambda: calls.append("start"),
        on_stop=lambda: calls.append("stop"),
        on_quit=lambda: calls.append("quit"),
        socket_path=tmp_path / "ctl.sock",
    )
    ctl.start()
    try:
        _send(ctl._socket_path, b"garbage")
        _pump()
        assert calls == []
    finally:
        ctl.close()


def test_close_removes_the_socket_file(tmp_path):
    path = tmp_path / "ctl.sock"
    ctl = ControlSocket(on_start=lambda: None, on_stop=lambda: None, on_quit=lambda: None, socket_path=path)
    assert path.exists()
    ctl.close()
    assert not path.exists()
