from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel

from app.services.generation import DEFAULT_MODEL, GenerationError, generate_structured


class Greeting(BaseModel):
    message: str


def _fake_response(text: str) -> Mock:
    # google-genai's real response object has a .text property with a
    # lot else attached to it - a bare Mock with just .text set is all
    # generate_structured actually reads, so that's all we need here.
    response = Mock()
    response.text = text
    return response


def test_generate_structured_returns_validated_instance():
    """The success path: a well-formed response gets parsed into the
    exact Pydantic type that was asked for, not just a dict.
    """
    with patch("app.services.generation._client") as mock_client:
        mock_client.models.generate_content.return_value = _fake_response(
            '{"message": "Hello, wonderful world!"}'
        )

        result = generate_structured("Say hello", response_schema=Greeting)

        assert isinstance(result, Greeting)
        assert result.message == "Hello, wonderful world!"


def test_generate_structured_passes_model_and_schema_to_the_api():
    """Confirms the actual wiring, not just error handling - that the
    prompt, the default model, and the schema all reach the real API
    call rather than being silently dropped or defaulted wrong.
    """
    with patch("app.services.generation._client") as mock_client:
        mock_client.models.generate_content.return_value = _fake_response(
            '{"message": "hi"}'
        )

        generate_structured("Say hello", response_schema=Greeting)

        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] == DEFAULT_MODEL
        assert call_kwargs["contents"] == "Say hello"
        assert call_kwargs["config"].response_schema is Greeting


def test_generate_structured_wraps_api_errors():
    """Whatever exception google-genai raises internally (network,
    auth, rate limit, a 503 like the one hit during manual testing),
    it should surface as OUR GenerationError - callers only need to
    catch one exception type, not know about the SDK's internals.
    """
    with patch("app.services.generation._client") as mock_client:
        mock_client.models.generate_content.side_effect = RuntimeError(
            "503 UNAVAILABLE: model overloaded"
        )

        with pytest.raises(GenerationError, match="Gemini API call failed"):
            generate_structured("Say hello", response_schema=Greeting)


def test_generate_structured_wraps_malformed_json():
    """If the response text isn't valid JSON at all, that should also
    become a GenerationError - not a raw JSONDecodeError leaking out
    of this module to whoever called it.
    """
    with patch("app.services.generation._client") as mock_client:
        mock_client.models.generate_content.return_value = _fake_response(
            "this is not json at all {{{"
        )

        with pytest.raises(GenerationError, match="didn't match the expected schema"):
            generate_structured("Say hello", response_schema=Greeting)


def test_generate_structured_wraps_schema_mismatch():
    """Valid JSON, but missing a required field - schema-constrained
    output makes this rare in practice, but it should still fail as
    GenerationError rather than an unhandled pydantic ValidationError.
    """
    with patch("app.services.generation._client") as mock_client:
        mock_client.models.generate_content.return_value = _fake_response(
            '{"wrong_field": "oops"}'
        )

        with pytest.raises(GenerationError, match="didn't match the expected schema"):
            generate_structured("Say hello", response_schema=Greeting)