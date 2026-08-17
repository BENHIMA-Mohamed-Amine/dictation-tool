import socket
import threading

import dictation_ctl


def _listen_once(path):
    """Binds a raw listening socket and returns (received, thread)."""
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(path))
    srv.listen(1)
    received = []

    def accept_one():
        conn, _ = srv.accept()
        with conn:
            received.append(conn.recv(64))
        srv.close()

    thread = threading.Thread(target=accept_one, daemon=True)
    thread.start()
    return received, thread


def test_send_returns_true_and_delivers_the_message(tmp_path, monkeypatch):
    sock_path = tmp_path / "ctl.sock"
    monkeypatch.setattr(dictation_ctl, "SOCKET_PATH", sock_path)
    received, thread = _listen_once(sock_path)

    assert dictation_ctl.send("stop") is True
    thread.join(timeout=2)
    assert received == [b"stop"]


def test_send_returns_false_when_nothing_is_listening(tmp_path, monkeypatch):
    monkeypatch.setattr(dictation_ctl, "SOCKET_PATH", tmp_path / "nobody-here.sock")
    assert dictation_ctl.send("start") is False


def test_stop_and_quit_are_noops_when_app_not_running(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(dictation_ctl, "SOCKET_PATH", tmp_path / "nobody-here.sock")
    monkeypatch.setattr("sys.argv", ["dictation_ctl.py", "stop"])
    assert dictation_ctl.main() == 0


def test_start_launches_the_app_when_not_running(tmp_path, monkeypatch):
    sock_path = tmp_path / "ctl.sock"
    monkeypatch.setattr(dictation_ctl, "SOCKET_PATH", sock_path)
    monkeypatch.setattr(dictation_ctl, "LAUNCH_TIMEOUT_SECONDS", 2)
    monkeypatch.setattr("sys.argv", ["dictation_ctl.py", "start"])

    launch_calls = []

    def fake_run(cmd, check):
        launch_calls.append(cmd)
        # Simulate the app coming up: bind the socket and accept the message.
        _listen_once(sock_path)

    monkeypatch.setattr(dictation_ctl.subprocess, "run", fake_run)

    assert dictation_ctl.main() == 0
    assert launch_calls == [[str(dictation_ctl.LAUNCHER), "start"]]
