import gi

gi.require_version("Gtk", "3.0")

from transcript_window import TranscriptWindow


def _text(window):
    return window._buffer_text()


def _type_at_start(window, text):
    window._buffer.insert(window._buffer.get_start_iter(), text)


def test_user_edit_survives_later_partials_and_finals():
    window = TranscriptWindow()
    window.append_final("hello world")

    _type_at_start(window, "EDIT: ")
    assert _text(window) == "EDIT: hello world"

    window.set_partial(" and then")
    assert _text(window) == "EDIT: hello world and then"

    window.append_final(" and then some")
    assert _text(window) == "EDIT: hello world and then some"


def test_partial_is_replaced_not_appended():
    window = TranscriptWindow()
    window.set_partial("he")
    window.set_partial("hello")
    assert _text(window) == "hello"


def test_new_segment_separates_and_keeps_edits():
    window = TranscriptWindow()
    window.append_final("first")
    _type_at_start(window, "X")
    window.begin_new_segment()
    window.append_final("second")
    assert _text(window) == "Xfirst\nsecond"
