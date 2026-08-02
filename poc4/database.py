"""Database dependencies for the FastAPI verification application."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from poc3.config import require_database_url


@lru_cache
def get_engine() -> Engine:
    """Create one reusable Engine without opening a connection at import time."""

    return create_engine(
        require_database_url(),
        echo=False,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


def get_session() -> Iterator[Session]:
    """Give each HTTP request its own short-lived SQLModel Session."""

    with Session(get_engine()) as session:
        yield session
