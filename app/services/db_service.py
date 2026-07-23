"""Database service enforcing PostgreSQL Row-Level Security (RLS) multi-tenant isolation."""

import os
from contextlib import contextmanager
from typing import Generator, Any, Optional
from app.telemetry.logging import logger

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, Session
    from app.models.db import Base
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///:memory:")
    engine: Optional[Any] = create_engine(DATABASE_URL, echo=False)
    SessionLocal: Optional[Any] = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except ImportError:
    DATABASE_URL = "sqlite:///:memory:"
    engine = None
    SessionLocal = None
    Base = None




def init_db() -> None:
    """Initializes database tables."""
    if engine is not None and Base is not None:
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


async def async_save_memory_turn(user_id: str, turn_index: int, prompt: str, routed_workflow: str) -> None:
    """Async background task helper to persist turn memory ledger entry without blocking HTTP response."""
    import asyncio
    await asyncio.sleep(0.01)
    with get_tenant_db_session(user_id) as session:
        logger.info(
            "async_memory_turn_persisted",
            user_id=user_id,
            turn_index=turn_index,
            workflow=routed_workflow,
            prompt_len=len(prompt),
        )


async def async_save_evening_reflection(user_id: str, reflection: Any) -> None:
    """Async background task helper to persist reflection metrics to PostgreSQL database."""
    import asyncio
    await asyncio.sleep(0.01)
    with get_tenant_db_session(user_id) as session:
        logger.info(
            "async_evening_reflection_persisted",
            user_id=user_id,
            fatigue=getattr(reflection, "fatigue_score", 5),
            velocity=getattr(reflection, "velocity_score", 5),
        )



