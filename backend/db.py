from __future__ import annotations

from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

try:
    from .config import settings
except ImportError:
    from config import settings


def _is_sqlite(database_url: str) -> bool:
    return database_url.startswith("sqlite:")


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    database_url = settings.database_url

    engine_kwargs: dict[str, Any] = {
        "future": True,
        "pool_pre_ping": True,
    }

    if _is_sqlite(database_url):
        # C3 FIX: Use StaticPool with check_same_thread=False, but also
        # enable WAL mode for safe concurrent reads + serialized writes.
        engine_kwargs.update(
            {
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            }
        )
    else:
        engine_kwargs.update(
            {
                "poolclass": QueuePool,
                "pool_size": int(getattr(settings, "db_pool_size", 20)),
                "max_overflow": int(getattr(settings, "db_max_overflow", 40)),
                "pool_timeout": int(getattr(settings, "db_pool_timeout", 30)),
                "pool_recycle": int(getattr(settings, "db_pool_recycle", 1800)),
                "connect_args": {"connect_timeout": 30},
            }
        )

    eng = create_engine(database_url, **engine_kwargs)

    # C3 FIX: Enable WAL mode and busy timeout for SQLite to handle
    # concurrent writes from ThreadPoolExecutor without "database is locked" errors.
    if _is_sqlite(database_url):
        @event.listens_for(eng, "connect")
        def _set_sqlite_pragmas(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return eng


SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False, expire_on_commit=False)

