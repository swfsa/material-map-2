from config import ConfigurationError, require_deepseek_api_key
from database import get_session
from deps import AppDeps
from repository import MaterialRepository


def main() -> None:
    require_deepseek_api_key()

    # 延迟导入，避免仅导入模块时就初始化外部模型。
    from agent import agent

    #创建数据库 Session；
    with get_session() as session:
        repo = MaterialRepository(session)
        deps = AppDeps(material_repo=repo)

        result = agent.run_sync(
            """
            分析 food_price_index 最近价格态势，
            生成简报。
            """,
            deps=deps,
        )

    print(result.output)


if __name__ == "__main__":
    try:
        main()
    except ConfigurationError as exc:
        raise SystemExit(f"配置错误：{exc}") from None
