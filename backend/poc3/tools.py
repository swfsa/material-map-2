import logging
from datetime import date
from typing import Annotated, Any

from pydantic import Field
from pydantic_ai import RunContext

from .deps import AppDeps
from .domain import MaterialCategory, SearchTimeLimit


logger = logging.getLogger(__name__)
MaterialQueryLimit = Annotated[int, Field(ge=1, le=100)]
WebResultLimit = Annotated[int, Field(ge=1, le=10)]


def register_tools(agent):
    @agent.tool
    def query_material(
        ctx: RunContext[AppDeps],
        sub_category: MaterialCategory,
        start_date: date | None = None,
        end_date: date | None = None,
        region: str | None = None,
        limit: MaterialQueryLimit = 20,
    ) -> list[dict[str, Any]]:
        """按分类、日期、地区和条数查询内部物资数据库。"""
        logger.info(
            "query_material category=%s start=%s end=%s region=%s limit=%s",
            sub_category,
            start_date,
            end_date,
            region,
            limit,
        )
        records = ctx.deps.material_repo.query_material(
            sub_category,
            start_date=start_date,
            end_date=end_date,
            region=region,
            limit=limit,
        )
        logger.info("query_material returned=%s", len(records))
        return [
            {
                "record_id": record.record_id,
                "category": record.sub_category,
                "period": record.period.isoformat() if record.period else None,
                "value": record.value,
                "unit": record.unit,
                "region": record.region,
                "source": record.source,
                "source_url": record.source_url,
                "confidence": record.confidence,
                "fetched_at": (
                    record.fetched_at.isoformat() if record.fetched_at else None
                ),
            }
            for record in records
        ]

    @agent.tool
    def web_search(
        ctx: RunContext[AppDeps],
        query: str,
        max_results: WebResultLimit = 5,
        time_limit: SearchTimeLimit | None = None,
    ) -> list[dict[str, Any]]:
        """搜索外部公开网页；涉及最新事件、政策或供应风险时使用。"""
        logger.info(
            "web_search query=%r max_results=%s time_limit=%s",
            query,
            max_results,
            time_limit,
        )
        results = ctx.deps.web_search_client.search(
            query,
            max_results=max_results,
            time_limit=time_limit,
        )
        logger.info("web_search returned=%s", len(results))
        return [result.model_dump(mode="json") for result in results]
