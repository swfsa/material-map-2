import logging

from .config import LOG_LEVEL

#允许用户手动传入日志等级。
def configure_logging(level: str | None = None) -> None:
    #选择日志等级
    selected_level = (level or LOG_LEVEL).upper()
    #转换成数字等级
    numeric_level = getattr(logging, selected_level, logging.INFO)

    #"配置日志系统"
    logging.basicConfig(
        level=numeric_level,
        #2026-07-31T15:30:10 INFO database 数据库连接成功
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        #控制%(asctime)s  2026-07-31T15:30:10
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    #降低 SQLAlchemy 日志

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
