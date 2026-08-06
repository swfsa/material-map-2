from datetime import date, timedelta

from .config import (
    ConfigurationError,
    require_database_url,
)
from .deps import AppDeps
from .llm_factory import create_llm_model, load_llm_config
from .logging_config import configure_logging
from .repository import (
    SessionPerQueryEnergyRepository,
    SessionPerQueryMaterialRepository,
)
from .report_service import generate_energy_report
from .search_factory import create_web_search_client


def main() -> None:
    configure_logging()
    require_database_url()
    llm_config = load_llm_config()
    llm_model = create_llm_model(llm_config)

    # 延迟导入外部资源，便于独立测试配置、Repository 和工具。
    from .database import get_session

    deps = AppDeps(
        # Pydantic AI 可能并行执行同步工具；每次数据库查询必须独占 Session。
        material_repo=SessionPerQueryMaterialRepository(get_session),
        web_search_client=create_web_search_client(),
    )
    end_date = date.today()
    generated = generate_energy_report(
        "分析最近一年的核心能源市场状态、趋势、波动、归因分析和风险并生成简报。",
        analysis_repository=SessionPerQueryEnergyRepository(get_session),
        agent_deps=deps,
        model=llm_model,
        start_date=end_date - timedelta(days=365),
        end_date=end_date,
    )

    from .database import create_report_table
    from .repository import ReportRepository

    create_report_table()
    with get_session() as session:
        ReportRepository(session).save(
            generated.report_ir,
            data_window_start=generated.analysis.data_window.start,
            data_window_end=generated.analysis.data_window.end,
        )
        session.commit()

    print(generated.report_ir.model_dump_json(indent=2))


if __name__ == "__main__":
    try:
        main()
    except ConfigurationError as exc:
        raise SystemExit(f"配置错误：{exc}") from None
