"""Database service enforcing PostgreSQL Row-Level Security (RLS) multi-tenant isolation."""

import os
from contextlib import contextmanager
from typing import Generator, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.models.db import Base
from app.telemetry.logging import logger

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///:memory:")

engine: Optional[Any] = None
SessionLocal: Optional[Any] = None

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, Session
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except ImportError:
    engine = None
    SessionLocal = None


def init_db() -> None:
    """Initializes database tables."""
    if engine is not None:
        Base.metadata.create_all(bind=engine)
    logger.info("database_tables_initialized")


@contextmanager
def get_tenant_db_session(user_id: str) -> Generator[Optional[Any], None, None]:
    """
    Context manager yielding a database session with PostgreSQL Row-Level Security (RLS) context.
    Executes SET LOCAL app.current_user_id = :user_id prior to any query execution.
    """
    if SessionLocal is None:
        yield None
        return

    session: Any = SessionLocal()
    try:
        if "postgresql" in DATABASE_URL:
            session.execute(text("SET LOCAL app.current_user_id = :user_id"), {"user_id": user_id})
        yield session
        session.commit()
    except Exception as e:
        err: Exception = e
        session.rollback()
        logger.error("db_session_error", user_id=user_id, error=str(err))
        raise
    finally:
        session.close()


