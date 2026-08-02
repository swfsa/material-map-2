"""对 LLM 协议做不读取业务数据的真实网络 smoke test。

示例：
    python -m mysql_demo2.verify_llm_api \
        --provider deepseek --api-style openai

    python -m mysql_demo2.verify_llm_api \
        --provider mimo --api-style anthropic
"""

from __future__ import annotations

import argparse

from pydantic_ai import Agent
from pydantic_ai.models import Model

from .config import ConfigurationError
from .llm_factory import (
    LLMConfig,
    create_llm_model,
    load_llm_config,
)


SMOKE_PROMPT = (
    "This is an API protocol smoke test. "
    "Reply with exactly PROTOCOL_SMOKE_OK and nothing else."
)


def run_protocol_smoke(
    config: LLMConfig,
    *,
    model: Model | None = None,
) -> str:
    """发送固定无敏感提示，返回模型文本；不注册任何业务工具。"""
    smoke_agent = Agent(
        model or create_llm_model(config),
        instructions=(
            "Follow the user's formatting instruction exactly. "
            "Do not call tools."
        ),
    )
    result = smoke_agent.run_sync(SMOKE_PROMPT)
    output = str(result.output).strip()
    if not output:
        raise RuntimeError("LLM API 已响应，但返回了空文本。")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "真实验证 OpenAI-compatible 或 Anthropic-compatible API；"
            "只发送固定测试文本，不读取数据库或调用 Web Search。"
        )
    )
    parser.add_argument(
        "--provider",
        help="provider profile 名；省略时读取 LLM_PROVIDER",
    )
    parser.add_argument(
        "--api-style",
        choices=("openai", "anthropic"),
        help="协议类型；省略时读取 LLM_API_STYLE/profile 默认值",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_llm_config(
        provider=args.provider,
        api_style=args.api_style,
    )
    output = run_protocol_smoke(config)
    print(
        "LLM_PROTOCOL_SMOKE_OK "
        f"provider={config.provider} "
        f"api_style={config.api_style} "
        f"model={config.model} "
        f"base_url={config.base_url}"
    )
    print(f"output={output}")


if __name__ == "__main__":
    try:
        main()
    except ConfigurationError as exc:
        raise SystemExit(f"配置错误：{exc}") from None
