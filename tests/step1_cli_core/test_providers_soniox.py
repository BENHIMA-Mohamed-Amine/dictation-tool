from unittest.mock import MagicMock, patch

from providers.base import Provider
from providers.soniox import SonioxProvider


def make_token(text, is_final):
    token = MagicMock()
    token.text = text
    token.is_final = is_final
    return token


def make_event(tokens, finished=False):
    event = MagicMock()
    event.tokens = tokens
    event.finished = finished
    return event


def test_soniox_provider_is_a_provider():
    assert issubclass(SonioxProvider, Provider)
    assert SonioxProvider.streaming is True


@patch("providers.soniox.SonioxClient")
def test_start_builds_config_with_keyterms_context(mock_client_cls):
    fake_session = MagicMock()
    fake_session.receive_events.return_value = iter([])
    mock_client_cls.return_value.realtime.stt.connect.return_value = fake_session

    provider = SonioxProvider()
    provider.configure(api_key="k", keyterms=["kubernetes", "Anthropic"])
    provider.start()
    provider.stop()

    _, kwargs = mock_client_cls.return_value.realtime.stt.connect.call_args
    config = kwargs["config"]
    assert config.context.terms == ["kubernetes", "Anthropic"]
    assert config.audio_format == "pcm_s16le"
    assert config.sample_rate == 16000
    assert config.num_channels == 1


@patch("providers.soniox.SonioxClient")
def test_feed_audio_and_stop_round_trip(mock_client_cls):
    fake_session = MagicMock()
    fake_session.receive_events.return_value = iter(
        [
            make_event([make_token("hel", False)]),
            make_event([make_token("hello", True)], finished=True),
        ]
    )
    mock_client_cls.return_value.realtime.stt.connect.return_value = fake_session

    partials = []
    finals = []

    provider = SonioxProvider()
    provider.configure(api_key="k", keyterms=["hello"])
    provider.start(on_partial=partials.append, on_final=finals.append)
    provider.feed_audio(b"\x00\x00")

    result = provider.stop()

    fake_session.enter.assert_called_once()
    fake_session.send_byte_chunk.assert_called_once_with(b"\x00\x00")
    fake_session.finalize.assert_called_once()
    fake_session.close.assert_called_once()
    assert partials == ["hel"]
    assert finals == ["hello"]
    assert result == "hello"


@patch("providers.soniox.SonioxClient")
def test_control_tokens_are_filtered_out(mock_client_cls):
    fake_session = MagicMock()
    fake_session.receive_events.return_value = iter(
        [
            make_event(
                [make_token("hello", True), make_token("<fin>", True)],
                finished=True,
            ),
        ]
    )
    mock_client_cls.return_value.realtime.stt.connect.return_value = fake_session

    provider = SonioxProvider()
    provider.configure(api_key="k")
    provider.start()

    result = provider.stop()

    assert result == "hello"
