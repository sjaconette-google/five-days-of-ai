"""SQLAlchemy ORM models for Cloud SQL PostgreSQL persistence."""

from datetime import datetime
from app.models.domain import GTDActionType, Chronotype

try:
    from sqlalchemy import (
        Column, String, Integer, Float, DateTime, Text, ForeignKey, LargeBinary, Enum as SQLEnum
    )
    from sqlalchemy.orm import declarative_base, relationship
    Base = declarative_base()
except ImportError:
    Column = String = Integer = Float = DateTime = Text = ForeignKey = LargeBinary = SQLEnum = relationship = lambda *args, **kwargs: None
    class Base:
        metadata = type("Meta", (), {"create_all": lambda bind: None})()




class UserSettingsDB(Base):
    """User profile and chronotype preferences table."""
    __tablename__ = "user_settings"

    user_id = Column(String(128), primary_key=True)
    email = Column(String(256), nullable=False, unique=True)
    chronotype = Column(SQLEnum(Chronotype), nullable=False, default=Chronotype.MORNING_LARK)
    max_daily_focus_hours = Column(Float, nullable=False, default=6.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tokens = relationship("UserOAuthTokensDB", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("GoalDB", back_populates="user", cascade="all, delete-orphan")


class UserOAuthTokensDB(Base):
    """Encrypted OAuth 2.0 access and refresh tokens table."""
    __tablename__ = "user_oauth_tokens"

    token_id = Column(String(128), primary_key=True)
    user_id = Column(String(128), ForeignKey("user_settings.user_id"), nullable=False)
    encrypted_access_token = Column(LargeBinary, nullable=False)
    encrypted_refresh_token = Column(LargeBinary, nullable=False)
    kms_key_id = Column(String(256), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("UserSettingsDB", back_populates="tokens")


class GoalDB(Base):
    """High-level user goals table."""
    __tablename__ = "goals"

    goal_id = Column(String(128), primary_key=True)
    user_id = Column(String(128), ForeignKey("user_settings.user_id"), nullable=False)
    title = Column(String(256), nullable=False)
    status = Column(String(64), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("UserSettingsDB", back_populates="goals")
    projects = relationship("ProjectDB", back_populates="goal", cascade="all, delete-orphan")


class ProjectDB(Base):
    """GTD Projects mapped to Google Tasks tasklists."""
    __tablename__ = "projects"

    project_id = Column(String(128), primary_key=True)
    goal_id = Column(String(128), ForeignKey("goals.goal_id"), nullable=True)
    user_id = Column(String(128), ForeignKey("user_settings.user_id"), nullable=False)
    google_tasklist_id = Column(String(128), nullable=True)
    title = Column(String(256), nullable=False)
    status = Column(String(64), nullable=False, default="ACTIVE")

    goal = relationship("GoalDB", back_populates="projects")
    next_steps = relationship("NextStepDB", back_populates="project", cascade="all, delete-orphan")


class NextStepDB(Base):
    """GTD Next Action steps mapped to Google Tasks."""
    __tablename__ = "next_steps"

    step_id = Column(String(128), primary_key=True)
    project_id = Column(String(128), ForeignKey("projects.project_id"), nullable=True)
    user_id = Column(String(128), ForeignKey("user_settings.user_id"), nullable=False)
    google_task_id = Column(String(128), nullable=True)
    title = Column(String(256), nullable=False)
    priority = Column(String(16), nullable=False, default="P1")
    status = Column(String(64), nullable=False, default="NEEDS_ACTION")

    project = relationship("ProjectDB", back_populates="next_steps")


class GTDEmailTaskMappingDB(Base):
    """Audit ledger mapping Gmail messages to GTD triage actions and created tasks."""
    __tablename__ = "gtd_email_task_mappings"

    mapping_id = Column(String(128), primary_key=True)
    user_id = Column(String(128), ForeignKey("user_settings.user_id"), nullable=False)
    gmail_message_id = Column(String(128), nullable=False)
    gtd_action = Column(SQLEnum(GTDActionType), nullable=False)
    google_task_id = Column(String(128), nullable=True)
    calendar_event_id = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DailyProgressLogDB(Base):
    """Evening shutdown logs recording velocity and fatigue reflection notes."""
    __tablename__ = "daily_progress_logs"

    log_id = Column(String(128), primary_key=True)
    user_id = Column(String(128), ForeignKey("user_settings.user_id"), nullable=False)
    date = Column(String(32), nullable=False)
    fatigue_score = Column(Integer, nullable=False)
    completed_tasks_count = Column(Integer, nullable=False)
    velocity_score = Column(Float, nullable=False)
    reflection_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
