import argparse

from .config import ConfigurationError, WEB_SEARCH_PROVIDER
from .logging_config import configure_logging
from .search_factory import create_web_search_client
from .search_models import WebSearchError


def main() -> None:
    parser = argparse.ArgumentParser(description="执行一次真实外部网络搜索")
    parser.add_argument(
        "query",
        nargs="?",
        default="OPEC crude oil supply latest",
    )
    parser.add_argument("--max-results", type=int, default=3)
    args = parser.parse_args()

    configure_logging()
    try:
        client = create_web_search_client()
        results = client.search(args.query, max_results=args.max_results)
    except (ConfigurationError, ValueError, WebSearchError) as exc:
        raise SystemExit(f"真实搜索验证失败：{exc}") from None

    if not results:
        raise SystemExit("真实搜索验证失败：服务未返回结果")

    print(f"真实搜索验证成功：provider={WEB_SEARCH_PROVIDER}，{len(results)} 条")
    for index, result in enumerate(results, start=1):
        print(f"{index}. {result.title}")
        print(f"   {result.url}")


if __name__ == "__main__":
    main()
