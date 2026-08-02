from collections.abc import Callable
from datetime import date, datetime, time
import hashlib
import json
from typing import Protocol

from sqlmodel import Session, select

from .domain import MATERIAL_CATEGORIES, MaterialCategory
from .models import MaterialRecord, ReportIRRecord
from .report import ReportIR


class MaterialQueryRepository(Protocol):
    """供 Agent 工具依赖的最小查询接口。"""

    def query_material(
        self,
        sub_category: MaterialCategory,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        region: str | None = None,
        limit: int = 20,
    ) -> list[MaterialRecord]: ...


class MaterialRepository:
    """绑定单个 Session 的底层 Repository。

    适合单元测试、导入事务，或由 SessionPerQueryMaterialRepository
    在一次查询的局部作用域中创建。不要跨线程共享实例。
    """

    def __init__(self, session: Session):
        self.session = session


    def query_material(
        self,
        sub_category: MaterialCategory,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        region: str | None = None,
        limit: int = 20,
    ) -> list[MaterialRecord]:
        """
        根据物资类别 sub_category，可选时间范围、地区，
        查询 MySQL 中最新的一批物资数据，并返回 MaterialRecord 对象列表。
        :param sub_category:
        :param start_date:
        :param end_date:
        :param region:
        :param limit:
        :return: MaterialRecord 对象列表
        """
        if sub_category not in MATERIAL_CATEGORIES:
            raise ValueError(f"不支持的分类：{sub_category}")
        if not 1 <= limit <= 100:
            raise ValueError("limit 必须在 1 到 100 之间")
        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date 不能晚于 end_date")

        statement = select(MaterialRecord).where(
            MaterialRecord.sub_category == sub_category
        )

        if start_date:
            statement = statement.where(
                MaterialRecord.period >= datetime.combine(start_date, time.min)
            )

        if end_date:
            statement = statement.where(
                MaterialRecord.period <= datetime.combine(end_date, time.max)
            )

        if region and region.strip():
            statement = statement.where(MaterialRecord.region == region.strip())

        #按照时间倒序。
        statement = statement.order_by(MaterialRecord.period.desc()).limit(limit)
        #SQLModel 执行
        return self.session.exec(statement).all()


class SessionPerQueryMaterialRepository:
    """
    为每次查询创建独立 Session，供并发 Agent 工具安全使用。
    什么时候创建数据库 Session，什么时候关闭 Session，以及保证并发安全。
    """

    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def query_material(
        self,
        sub_category: MaterialCategory,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        region: str | None = None,
        limit: int = 20,
    ) -> list[MaterialRecord]:
        # Pydantic AI 会在线程池中执行同步工具。Session 必须在同一个
        # 工作线程内创建、使用并关闭，不能由 main.py 跨线程持有。
        with self._session_factory() as session:
            repository = MaterialRepository(session)
            return repository.query_material(
                sub_category,
                start_date=start_date,
                end_date=end_date,
                region=region,
                limit=limit,
            )


def report_content_sha256(report: ReportIR) -> str:
    """为同一份 ReportIR 生成稳定哈希，用于幂等导入。"""

    canonical_json = json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class ReportRepository:
    """保存 Agent 生成的 ReportIR，并避免重复写入同一份报告。"""

    def __init__(self, session: Session):
        self.session = session

    def save(self, report: ReportIR) -> tuple[ReportIRRecord, bool]:
        content_sha256 = report_content_sha256(report)
        existing = self.session.exec(
            select(ReportIRRecord).where(
                ReportIRRecord.content_sha256 == content_sha256
            )
        ).first()
        if existing is not None:
            return existing, False

        row = ReportIRRecord(
            content_sha256=content_sha256,
            title=report.title,
            data_window_start=report.data_window.start,
            data_window_end=report.data_window.end,
            report_json=report.model_dump(mode="json"),
        )
        self.session.add(row)
        self.session.flush()
        return row, True
