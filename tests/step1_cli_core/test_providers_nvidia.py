from unittest.mock import MagicMock, patch

from providers.base import Provider
from providers.nvidia import NEMOTRON_ASR_STREAMING_FUNCTION_ID, NVCF_URI, NvidiaProvider


def make_result(text, is_final):
    alternative = MagicMock()
    alternative.transcript = text
    result = MagicMock()
    result.alternatives = [alternative]
    result.is_final = is_final
    return result


def make_response(results):
    response = MagicMock()
    response.results = results
    return response


def test_nvidia_provider_is_a_provider():
    assert issubclass(NvidiaProvider, Provider)
    assert NvidiaProvider.streaming is True


@patch("providers.nvidia.riva.client.Auth")
@patch("providers.nvidia.riva.client.ASRService")
def test_start_builds_auth_with_hosted_nim_endpoint_and_function_id(mock_asr_service_cls, mock_auth_cls):
    mock_asr_service_cls.return_value.streaming_response_generator.return_value = iter([])

    provider = NvidiaProvider()
    provider.configure(api_key="my-key")
    provider.start()
    provider.stop()

    _, kwargs = mock_auth_cls.call_args
    assert kwargs["uri"] == NVCF_URI
    assert kwargs["use_ssl"] is True
    assert ["function-id", NEMOTRON_ASR_STREAMING_FUNCTION_ID] in kwargs["metadata_args"]
    assert ["authorization", "Bearer my-key"] in kwargs["metadata_args"]


@patch("providers.nvidia.riva.client.add_word_boosting_to_config")
@patch("providers.nvidia.riva.client.Auth")
@patch("providers.nvidia.riva.client.ASRService")
def test_keyterms_apply_word_boosting(mock_asr_service_cls, mock_auth_cls, mock_add_boosting):
    mock_asr_service_cls.return_value.streaming_response_generator.return_value = iter([])

    provider = NvidiaProvider()
    provider.configure(api_key="k", keyterms=["kubernetes", "Anthropic"])
    provider.start()
    provider.stop()

    args, _ = mock_add_boosting.call_args
    assert args[1] == ["kubernetes", "Anthropic"]


@patch("providers.nvidia.riva.client.Auth")
@patch("providers.nvidia.riva.client.ASRService")
def test_feed_audio_and_stop_round_trip(mock_asr_service_cls, mock_auth_cls):
    mock_asr_service_cls.return_value.streaming_response_generator.return_value = iter(
        [
            make_response([make_result("hel", False)]),
            make_response([make_result("hello", True)]),
        ]
    )

    partials = []
    finals = []

    provider = NvidiaProvider()
    provider.configure(api_key="k")
    provider.start(on_partial=partials.append, on_final=finals.append)
    provider.feed_audio(b"\x00\x00")

    result = provider.stop()

    assert partials == ["hel"]
    assert finals == ["hello"]
    assert result == "hello"


@patch("providers.nvidia.riva.client.Auth")
@patch("providers.nvidia.riva.client.ASRService")
def test_stop_ends_the_audio_generator_without_hanging(mock_asr_service_cls, mock_auth_cls):
    consumed_chunks = []

    def fake_streaming_response_generator(audio_chunks, streaming_config):
        for chunk in audio_chunks:
            consumed_chunks.append(chunk)
        return iter([])

    mock_asr_service_cls.return_value.streaming_response_generator.side_effect = fake_streaming_response_generator

    provider = NvidiaProvider()
    provider.configure(api_key="k")
    provider.start()
    provider.feed_audio(b"chunk1")
    provider.feed_audio(b"chunk2")

    result = provider.stop()  # must return promptly, not hang waiting on the queue

    assert consumed_chunks == [b"chunk1", b"chunk2"]
    assert result == ""


@patch("providers.nvidia.riva.client.Auth")
@patch("providers.nvidia.riva.client.ASRService")
def test_listener_errors_are_printed_not_silently_swallowed(mock_asr_service_cls, mock_auth_cls, capsys):
    def raise_permission_denied(audio_chunks, streaming_config):
        raise RuntimeError("PERMISSION_DENIED: Authorization failed")
        yield  # pragma: no cover - makes this a generator function

    mock_asr_service_cls.return_value.streaming_response_generator.side_effect = raise_permission_denied

    provider = NvidiaProvider()
    provider.configure(api_key="k")
    provider.start()

    result = provider.stop()  # must not hang or raise out of stop()

    assert result == ""
    assert "PERMISSION_DENIED" in capsys.readouterr().out
