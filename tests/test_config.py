import pytest
from writer_agent.settings import Settings, guess_context_from_model_name


def test_default_settings():
    s = Settings()
    assert s.lmstudio.url == "http://localhost:1234/v1"
    assert s.lmstudio.model_name == ""
    assert s.generation.temperature == 0.85
    assert s.context.budget_tokens == 6000


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("WRITER_LM_STUDIO_URL", "http://custom:9999/v1")
    monkeypatch.setenv("WRITER_MODEL_NAME", "my-model")
    monkeypatch.setenv("WRITER_TEMPERATURE", "0.5")
    s = Settings.load()
    assert s.lmstudio.url == "http://custom:9999/v1"
    assert s.lmstudio.model_name == "my-model"
    assert s.generation.temperature == 0.5
    _, src = s.get_value("generation.temperature")
    assert src == "env"


def test_toml_cascade(tmp_path):
    # Global config
    global_path = tmp_path / "global" / "config.toml"
    global_path.parent.mkdir(parents=True)
    global_path.write_text('[generation]\ntemperature = 0.7\n', encoding="utf-8")

    # Local config overrides
    local_path = tmp_path / "project" / "writer.toml"
    local_path.parent.mkdir(parents=True)
    local_path.write_text('[generation]\ntemperature = 0.95\n', encoding="utf-8")

    original = Settings._global_path
    Settings._global_path = classmethod(lambda cls: global_path)
    try:
        s = Settings.load(local_dir=tmp_path / "project")
        assert s.generation.temperature == 0.95  # local wins
        _, src = s.get_value("generation.temperature")
        assert src == "local"
    finally:
        Settings._global_path = original


def test_model_auto_detect():
    caps = guess_context_from_model_name("qwen2.5-7b-instruct-q4_k_m")
    assert caps["max_context_tokens"] == 131072
    assert caps["supports_reasoning"] is False

    caps2 = guess_context_from_model_name("deepseek-r1-32b")
    assert caps2["supports_reasoning"] is True

    caps3 = guess_context_from_model_name("llama-3.1-8b")
    assert caps3["max_context_tokens"] == 131072


def test_set_and_get_value():
    s = Settings()
    s.set_value("generation.temperature", "0.99", scope="local")
    val, src = s.get_value("generation.temperature")
    assert val == 0.99
    assert src == "local"


def test_invalid_key_raises():
    s = Settings()
    with pytest.raises(ValueError, match="Invalid key"):
        s.get_value("invalid_key")
    with pytest.raises(ValueError, match="Unknown section"):
        s.get_value("nonexistent.field")
    with pytest.raises(ValueError, match="Unknown field"):
        s.get_value("generation.nonexistent")


def test_api_capabilities_resolve():
    s = Settings()
    assert s.model_overrides.max_context_tokens == 0  # not set
    s.resolve(api_capabilities={"max_context_tokens": 32768, "max_output_tokens": 8192})
    assert s.model_overrides.max_context_tokens == 32768
    _, src = s.get_value("model_overrides.max_context_tokens")
    assert src == "api"
