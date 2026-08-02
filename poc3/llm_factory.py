"""根据环境变量创建可替换、可切换协议的 LLM 模型。

Agent、工具和报告结构不关心具体供应商或 API 协议；只有本模块知道如何把
DeepSeek、MiMo、百炼或其他 OpenAI/Anthropic-compatible 服务转换为
Pydantic AI 模型。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Literal, cast
from urllib.parse import urlparse

from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.alibaba import AlibabaProvider
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_ai.providers.openai import OpenAIProvider

from .config import ConfigurationError


APIStyle = Literal["openai", "anthropic"]

_PROVIDER_ALIASES = {
    "aliyun": "bailian",
    "alibaba": "bailian",
    "dashscope": "bailian",
    "qwen": "bailian",
    "xiaomi": "mimo",
    "openai-compatible": "custom",
    "openai_compatible": "custom",
}

_DEFAULT_API_STYLES: dict[str, APIStyle] = {
    "anthropic": "anthropic",
}

_DEFAULT_BASE_URLS = {
    ("deepseek", "openai"): "https://api.deepseek.com",
    ("bailian", "openai"): "https://dashscope.aliyuncs.com/compatible-mode/v1",
    ("openai", "openai"): "https://api.openai.com/v1",
    ("anthropic", "anthropic"): "https://api.anthropic.com",
    ("mimo", "openai"): "https://api.xiaomimimo.com/v1",
    ("mimo", "anthropic"): "https://api.xiaomimimo.com/anthropic",
}


@dataclass(frozen=True)
class LLMConfig:
    """一次 LLM 调用所需的完整配置。

    `api_key` 不参与 repr，避免调试输出意外泄漏真实密钥。
    """

    provider: str   #模型供应商
    api_style: APIStyle    #openAI or anthropic
    model: str      #模型名称
    base_url: str
    api_key: str = field(repr=False)


def _normalize_provider(value: str) -> str:
    provider = value.strip().lower() or "deepseek"
    return _PROVIDER_ALIASES.get(provider, provider)


def _provider_prefix(provider: str) -> str:
    """把 provider 名转换为可用于环境变量的前缀。"""
    return re.sub(r"[^A-Z0-9]+", "_", provider.upper()).strip("_")


def _normalize_api_style(value: str) -> APIStyle:
    normalized = value.strip().lower().replace("_", "-")
    aliases = {
        "openai-compatible": "openai",
        "anthropic-compatible": "anthropic",
        "claude": "anthropic",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"openai", "anthropic"}:
        raise ConfigurationError(
            "LLM_API_STYLE 必须是 openai 或 anthropic。"
        )
    return cast(APIStyle, normalized)


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _model_env_names(
    provider: str,
    api_style: APIStyle,
) -> tuple[str, ...]:
    prefix = _provider_prefix(provider)
    style_prefix = api_style.upper()
    return (
        "LLM_MODEL",
        f"{prefix}_{style_prefix}_MODEL",
        f"{prefix}_MODEL",
    )


def _key_env_names(
    provider: str,
    api_style: APIStyle,
) -> tuple[str, ...]:
    prefix = _provider_prefix(provider)
    style_prefix = api_style.upper()
    names = [
        "LLM_API_KEY",
        f"{prefix}_{style_prefix}_API_KEY",
        f"{prefix}_API_KEY",
    ]
    if provider == "bailian":
        names.extend(["DASHSCOPE_API_KEY", "ALIBABA_API_KEY"])
    return tuple(names)


def _base_url_env_names(
    provider: str,
    api_style: APIStyle,
) -> tuple[str, ...]:
    prefix = _provider_prefix(provider)
    style_prefix = api_style.upper()
    return (
        "LLM_BASE_URL",
        f"{prefix}_{style_prefix}_BASE_URL",
        f"{prefix}_BASE_URL",
    )


def _normalize_model_name(provider: str, model: str) -> str:
    """兼容旧的 `deepseek:model-name` 等写法。"""
    prefix = f"{provider}:"
    if model.lower().startswith(prefix):
        return model[len(prefix) :]
    return model


def _validate_base_url(base_url: str) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigurationError(
            "LLM Base URL 必须是完整的 http/https 地址，"
            "请检查 LLM_BASE_URL 或当前供应商的 *_BASE_URL。"
        )


def load_llm_config(
    provider: str | None = None,
    api_style: str | None = None,
) -> LLMConfig:
    """解析当前供应商与协议配置。

    每个值的优先级：
    1. LLM_API_KEY / LLM_MODEL / LLM_BASE_URL
    2. <PROVIDER>_<STYLE>_API_KEY / MODEL / BASE_URL
    3. <PROVIDER>_API_KEY / MODEL / BASE_URL
    4. 已知 provider + style 的默认 Base URL
    """
    resolved_provider = _normalize_provider(
        provider or os.getenv("LLM_PROVIDER", "deepseek")
    )
    prefix = _provider_prefix(resolved_provider)
    style_value = (
        api_style
        or os.getenv("LLM_API_STYLE", "").strip()
        or os.getenv(f"{prefix}_API_STYLE", "").strip()
        or _DEFAULT_API_STYLES.get(resolved_provider, "openai")
    )
    resolved_style = _normalize_api_style(style_value)

    model = _first_env(
        *_model_env_names(resolved_provider, resolved_style)
    )
    if not model:
        raise ConfigurationError(
            f"未配置 {resolved_provider}/{resolved_style} 的模型。"
            f"请填写 LLM_MODEL、{prefix}_{resolved_style.upper()}_MODEL "
            f"或 {prefix}_MODEL。"
        )
    model = _normalize_model_name(resolved_provider, model)

    api_key = _first_env(
        *_key_env_names(resolved_provider, resolved_style)
    )
    if not api_key:
        raise ConfigurationError(
            f"未配置 {resolved_provider}/{resolved_style} 的 API Key。"
            f"请填写 LLM_API_KEY、"
            f"{prefix}_{resolved_style.upper()}_API_KEY 或 {prefix}_API_KEY。"
        )

    base_url = _first_env(
        *_base_url_env_names(resolved_provider, resolved_style)
    )
    if not base_url:
        base_url = _DEFAULT_BASE_URLS.get(
            (resolved_provider, resolved_style),
            "",
        )
    if not base_url:
        raise ConfigurationError(
            f"{resolved_provider}/{resolved_style} 没有内置 Base URL。"
            f"请填写 LLM_BASE_URL、"
            f"{prefix}_{resolved_style.upper()}_BASE_URL "
            f"或 {prefix}_BASE_URL。"
        )
    _validate_base_url(base_url)

    return LLMConfig(
        provider=resolved_provider,
        api_style=resolved_style,
        model=model,
        base_url=base_url,
        api_key=api_key,
    )


def create_llm_model(config: LLMConfig | None = None) -> Model:
    """创建 Pydantic AI 模型，不发起网络请求。"""
    resolved = config or load_llm_config()

    if resolved.api_style == "anthropic":
        provider = AnthropicProvider(
            api_key=resolved.api_key,
            base_url=resolved.base_url,
        )
        return AnthropicModel(
            resolved.model,
            provider=provider,
        )

    if resolved.provider == "deepseek":
        if resolved.base_url.rstrip("/") == _DEFAULT_BASE_URLS[
            ("deepseek", "openai")
        ]:
            openai_provider = DeepSeekProvider(api_key=resolved.api_key)
        else:
            # 私有网关仍保留 DeepSeek 的工具调用和 reasoning profile。
            custom_provider = OpenAIProvider(
                api_key=resolved.api_key,
                base_url=resolved.base_url,
            )
            return OpenAIChatModel(
                resolved.model,
                provider=custom_provider,
                profile=DeepSeekProvider.model_profile(resolved.model),
            )
    elif resolved.provider == "bailian":
        openai_provider = AlibabaProvider(
            api_key=resolved.api_key,
            base_url=resolved.base_url,
        )
    else:
        openai_provider = OpenAIProvider(
            api_key=resolved.api_key,
            base_url=resolved.base_url,
        )

    return OpenAIChatModel(
        resolved.model,
        provider=openai_provider,
    )
