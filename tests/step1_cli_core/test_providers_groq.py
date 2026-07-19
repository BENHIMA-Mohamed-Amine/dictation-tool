from unittest.mock import MagicMock, patch

from providers.base import Provider
from providers.groq import GroqProvider


def test_groq_provider_is_a_provider():
    assert issubclass(GroqProvider, Provider)
    assert GroqProvider.streaming is False


def test_configure_builds_prompt_from_keyterms():
    provider = GroqProvider()
    provider.configure(api_key="k", keyterms=["kubernetes", "Anthropic"])
    assert provider.prompt == "kubernetes, Anthropic"


def test_configure_with_no_keyterms_has_no_prompt():
    provider = GroqProvider()
    provider.configure(api_key="k", keyterms=[])
    assert provider.prompt is None


@patch("providers.groq.requests.post")
def test_stop_posts_to_groq_and_returns_transcript(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "hello world"}
    mock_post.return_value = mock_response

    provider = GroqProvider()
    provider.configure(api_key="secret-key", keyterms=["hello"])
    provider.start()
    provider.feed_audio(b"\x00\x00" * 100)

    result = provider.stop()

    assert result == "hello world"
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer secret-key"
    assert kwargs["data"]["prompt"] == "hello"
    assert "file" in kwargs["files"]
