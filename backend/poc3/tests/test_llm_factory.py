import pytest
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel

from poc3.config import ConfigurationError
from poc3.llm_factory import (
    LLMConfig,
    create_llm_model,
    load_llm_config,
)
from poc3.verify_llm_api import run_protocol_smoke


_ENV_NAMES = (
    "LLM_PROVIDER",
    "LLM_API_STYLE",
    "LLM_API_KEY",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_MODEL",
    "DEEPSEEK_BASE_URL",
    "MIMO_API_KEY",
    "MIMO_MODEL",
    "MIMO_BASE_URL",
    "MIMO_API_STYLE",
    "MIMO_OPENAI_BASE_URL",
    "MIMO_ANTHROPIC_BASE_URL",
    "MIMO_OPENAI_API_KEY",
    "MIMO_ANTHROPIC_API_KEY",
    "MIMO_OPENAI_MODEL",
    "MIMO_ANTHROPIC_MODEL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_BASE_URL",
    "BAILIAN_API_KEY",
    "BAILIAN_MODEL",
    "BAILIAN_BASE_URL",
    "DASHSCOPE_API_KEY",
    "ALIBABA_API_KEY",
    "SILICON_FLOW_API_KEY",
    "SILICON_FLOW_MODEL",
    "SILICON_FLOW_BASE_URL",
)


def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_loads_legacy_deepseek_profile_and_hides_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-deepseek-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek:deepseek-v4-pro")

    config = load_llm_config()
    model = create_llm_model(config)

    assert config.provider == "deepseek"
    assert config.api_style == "openai"
    assert config.model == "deepseek-v4-pro"
    assert config.base_url == "https://api.deepseek.com"
    assert "secret-deepseek-key" not in repr(config)
    assert model.system == "deepseek"
    assert model.model_name == "deepseek-v4-pro"


def test_loads_bailian_alias_with_beijing_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "aliyun")
    monkeypatch.setenv("BAILIAN_API_KEY", "test-bailian-key")
    monkeypatch.setenv("BAILIAN_MODEL", "qwen-plus")

    config = load_llm_config()
    model = create_llm_model(config)

    assert config.provider == "bailian"
    assert config.base_url == (
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    assert model.system == "alibaba"
    assert model.model_name == "qwen-plus"


def test_mimo_switches_between_openai_and_anthropic_protocols(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "mimo")
    monkeypatch.setenv("MIMO_API_KEY", "test-mimo-key")
    monkeypatch.setenv("MIMO_MODEL", "mimo-v2.5-pro")

    openai_config = load_llm_config(api_style="openai")
    openai_model = create_llm_model(openai_config)
    anthropic_config = load_llm_config(api_style="anthropic")
    anthropic_model = create_llm_model(anthropic_config)

    assert openai_config.api_style == "openai"
    assert openai_config.base_url == "https://api.xiaomimimo.com/v1"
    assert isinstance(openai_model, OpenAIChatModel)
    assert anthropic_config.api_style == "anthropic"
    assert anthropic_config.base_url == (
        "https://api.xiaomimimo.com/anthropic"
    )
    assert isinstance(anthropic_model, AnthropicModel)


def test_supports_future_provider_without_code_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "silicon-flow")
    monkeypatch.setenv("SILICON_FLOW_API_KEY", "test-future-key")
    monkeypatch.setenv("SILICON_FLOW_MODEL", "future-model")
    monkeypatch.setenv(
        "SILICON_FLOW_BASE_URL",
        "https://future.example.com/v1",
    )

    config = load_llm_config()
    model = create_llm_model(config)

    assert config.provider == "silicon-flow"
    assert config.model == "future-model"
    assert model.base_url == "https://future.example.com/v1/"


def test_generic_values_override_provider_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "provider-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "provider-model")
    monkeypatch.setenv("LLM_API_KEY", "override-key")
    monkeypatch.setenv("LLM_MODEL", "override-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://gateway.example.com/v1")

    config = load_llm_config()

    assert config.api_key == "override-key"
    assert config.api_style == "openai"
    assert config.model == "override-model"
    assert config.base_url == "https://gateway.example.com/v1"


def test_rejects_invalid_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "mimo")
    monkeypatch.setenv("MIMO_API_KEY", "test-key")
    monkeypatch.setenv("MIMO_MODEL", "test-model")
    monkeypatch.setenv("MIMO_BASE_URL", "not-a-url")

    with pytest.raises(ConfigurationError, match="完整的 http/https 地址"):
        load_llm_config()


def test_protocol_specific_values_override_common_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "mimo")
    monkeypatch.setenv("MIMO_API_KEY", "common-key")
    monkeypatch.setenv("MIMO_MODEL", "common-model")
    monkeypatch.setenv(
        "MIMO_ANTHROPIC_BASE_URL",
        "https://anthropic-gateway.example.com",
    )
    monkeypatch.setenv("MIMO_ANTHROPIC_MODEL", "anthropic-model")

    config = load_llm_config(api_style="anthropic")

    assert config.api_key == "common-key"
    assert config.model == "anthropic-model"
    assert config.base_url == "https://anthropic-gateway.example.com"


def test_rejects_unknown_api_style(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("LLM_API_STYLE", "responses")

    with pytest.raises(ConfigurationError, match="openai 或 anthropic"):
        load_llm_config()


def test_protocol_smoke_does_not_need_business_dependencies() -> None:
    config = LLMConfig(
        provider="offline",
        api_style="anthropic",
        model="offline-model",
        base_url="https://offline.example.com",
        api_key="offline-key",
    )

    output = run_protocol_smoke(
        config,
        model=TestModel(custom_output_text="PROTOCOL_SMOKE_OK"),
    )

    assert output == "PROTOCOL_SMOKE_OK"
