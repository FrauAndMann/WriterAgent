import pytest
from writer_agent.config import Config


def test_default_config():
    config = Config()
    assert config.lm_studio_url == "http://localhost:1234/v1"
    assert config.model_name == ""  # auto-detect from LM Studio
    assert config.max_context_tokens == 8192
    assert config.db_path.name == "writer_agent.db"


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("WRITER_LM_STUDIO_URL", "http://custom:9999/v1")
    monkeypatch.setenv("WRITER_MODEL_NAME", "my-model")
    monkeypatch.setenv("WRITER_MAX_CONTEXT_TOKENS", "32768")
    config = Config.from_env()
    assert config.lm_studio_url == "http://custom:9999/v1"
    assert config.model_name == "my-model"
    assert config.max_context_tokens == 32768
