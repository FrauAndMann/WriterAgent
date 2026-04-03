import pytest
from unittest.mock import MagicMock, patch
from writer_agent.llm.client import LLMClient
from writer_agent.settings import Settings


def test_client_uses_openai_compatible_api():
    settings = Settings()
    settings.lmstudio.url = "http://localhost:1234/v1"
    settings.lmstudio.model_name = "test-model"
    client = LLMClient(settings)
    assert client.base_url == "http://localhost:1234/v1"
    assert client.model == "test-model"


def test_generate_sends_correct_params(mocker):
    client = LLMClient(Settings())
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Generated text"
    mocker.patch.object(client, "_client")
    client._client.chat.completions.create.return_value = mock_response

    result = client.generate(
        system_prompt="You are a writer.",
        user_prompt="Write something dark.",
        max_tokens=2000,
    )
    assert result == "Generated text"
    client._client.chat.completions.create.assert_called_once()


def test_generate_with_context_assembles_messages(mocker):
    client = LLMClient(Settings())
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Dark prose"
    mocker.patch.object(client, "_client")
    client._client.chat.completions.create.return_value = mock_response

    result = client.generate(
        system_prompt="System",
        user_prompt="Write chapter 1",
        context_blocks=["Previous summary...", "Character: Elena is cold"],
        max_tokens=4000,
    )
    assert result == "Dark prose"
    call_args = client._client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    assert len(messages) >= 3  # system + context + user


def test_auto_detect_model(mocker):
    settings = Settings()
    settings.lmstudio.model_name = ""
    client = LLMClient(settings)
    mock_models = MagicMock()
    mock_models.data = [MagicMock(id="local-model-q4_k_m")]
    mocker.patch.object(client, "_client")
    client._client.models.list.return_value = mock_models
    model = client.get_available_model()
    assert model == "local-model-q4_k_m"
