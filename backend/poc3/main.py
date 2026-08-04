from .config import (
    ConfigurationError,
    require_database_url,
)
from .deps import AppDeps
from .llm_factory import create_llm_model, load_llm_config
from .logging_config import configure_logging
from .repository import SessionPerQueryMaterialRepository
from .search_factory import create_web_search_client


def main() -> None:
    configure_logging()
    require_database_url()
    llm_config = load_llm_config()
    llm_model = create_llm_model(llm_config)

    # 延迟导入外部资源，便于独立测试配置、Repository 和工具。
    from .agent import agent
    from .database import get_session

    deps = AppDeps(
        # Pydantic AI 可能并行执行同步工具；每次数据库查询必须独占 Session。
        material_repo=SessionPerQueryMaterialRepository(get_session),
        web_search_client=create_web_search_client(),
    )
    result = agent.run_sync(
        """
        分析 crude_oil 最近价格态势并生成简报。
        先使用内部数据；如果需要解释近期原因，再搜索外部公开信息。
        """,
        deps=deps,
        model=llm_model,
    )

    from .database import create_report_table
    from .repository import ReportRepository

    create_report_table()
    with get_session() as session:
        ReportRepository(session).save(result.output)
        session.commit()

    print(result.output.model_dump_json(indent=2))


if __name__ == "__main__":
    try:
        main()
    except ConfigurationError as exc:
        raise SystemExit(f"配置错误：{exc}") from None
