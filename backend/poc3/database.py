from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, Session, create_engine

from .config import require_database_url

"""
数据库配置
  |
Engine      管理数据库连接
  |
  |
  创建
  |
  ↓

Session     执行数据库操作
  |
  |
  执行SQL
  |
  ↓

Database
"""
@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """从私密环境配置创建进程内唯一的 Engine。"""
    return create_engine(
        require_database_url(),
        echo=False,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


def get_session() -> Session:
    """为什么要传engine?因为本地可能有多个数据库、使用engine告诉使用这个数据库连接配置"""
    return Session(get_engine())


def create_report_table() -> None:
    """仅创建 ReportIR 持久化表，不改动已有业务表。"""

    from .models import ReportIRRecord

    SQLModel.metadata.create_all(
        get_engine(),
        tables=[ReportIRRecord.__table__],
        checkfirst=True,
    )
