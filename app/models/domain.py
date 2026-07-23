"""Domain data models and declarative Pydantic v2 contracts."""

from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class GTDActionType(str, Enum):
    """Getting Things Done triage classification actions."""
    CONVERT_TO_TASK = "CONVERT_TO_TASK"
    MOVE_TO_REFERENCE = "MOVE_TO_REFERENCE"
    SNOOZE_DEFER = "SNOOZE_DEFER"
    NO_ACTION_NEEDED = "NO_ACTION_NEEDED"


class Chronotype(str, Enum):
    """User diurnal chronotype profiles."""
    MORNING_LARK = "MORNING_LARK"
    NIGHT_OWL = "NIGHT_OWL"


class WorkflowType(str, Enum):
    """System workflow types."""
    INBOX_TRIAGE = "INBOX_TRIAGE"
    DAILY_PLANNING = "DAILY_PLANNING"
    EVENING_SHUTDOWN = "EVENING_SHUTDOWN"
    WORKSPACE_MUTATION = "WORKSPACE_MUTATION"


class BaseStrictModel(BaseModel):
    """Base Pydantic v2 model enforcing strict schema validation with extra='forbid'."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class GmailMessage(BaseStrictModel):
    """Representation of an incoming Gmail message payload."""
    id: str = Field(..., description="Unique Gmail message identifier.")
    thread_id: str = Field(..., description="Gmail thread ID.")
    sender: str = Field(..., description="Sender email address.")
    recipient: str = Field(..., description="Recipient email address.")
    subject: str = Field(..., description="Email subject line.")
    snippet: str = Field(..., description="Short snippet preview.")
    body_text: str = Field(..., description="Full or scrubbed body text.")
    received_at: str = Field(..., description="Timestamp ISO string when message was received.")


class GTDInboxDecision(BaseStrictModel):
    """Structured decision output from inbox triage analysis."""
    message_id: str = Field(..., description="Target Gmail message ID.")
    gtd_action: GTDActionType = Field(..., description="Assigned GTD classification.")
    target_project_id: Optional[str] = Field(None, description="Optional target project TaskList ID.")
    next_action_title: Optional[str] = Field(None, description="Generated action title for Google Tasks.")
    reasoning: Optional[str] = Field(None, description="Cognitive rationale for the decision.")


class TriageToolContract(BaseStrictModel):
    """Contract for executing interactive inbox triage decisions."""
    message_id: str = Field(..., description="Target Gmail message ID.")
    action_type: GTDActionType = Field(..., description="Selected GTD action.")
    target_project_id: Optional[str] = Field(None, description="Target Project TaskList ID.")
    next_action_title: Optional[str] = Field(None, description="Generated Google Task title.")


class CapacityPlanningContract(BaseStrictModel):
    """Contract for matching task commitments against energy budgets."""
    user_id: str = Field(..., description="Target user identifier.")
    current_fatigue_score: int = Field(..., ge=1, le=10, description="Self-reported fatigue score on a 1-10 scale.")
    frog_task_id: str = Field(..., description="Primary focus task ID (P0 Frog).")
    support_task_ids: List[str] = Field(..., description="List of 3-5 support task IDs.")


class CalendarFocusBlock(BaseStrictModel):
    """Focus time block item on secondary sub-calendar."""
    title: str = Field(..., description="Event title for focus block.")
    start_time: str = Field(..., description="Start ISO timestamp.")
    end_time: str = Field(..., description="End ISO timestamp.")
    task_id: str = Field(..., description="Associated Google Task ID.")


class DailyCommitmentPlan(BaseStrictModel):
    """Fitted daily capacity commitment schedule draft."""
    plan_date: str = Field(..., description="Target plan date ISO format (YYYY-MM-DD).")
    frog_task_id: str = Field(..., description="Primary outcome task ID (P0 Frog).")
    support_task_ids: List[str] = Field(..., description="Fitted supporting task IDs (3-5 items).")
    total_estimated_duration_minutes: int = Field(..., ge=0, description="Total duration of all scheduled tasks in minutes.")
    available_capacity_minutes: int = Field(..., ge=0, description="Available free calendar capacity in minutes.")
    alignment_notes: str = Field(..., description="Chronotype and energy alignment explanation.")
    focus_blocks: List[CalendarFocusBlock] = Field(default_factory=list, description="Scheduled focus time blocks.")


class HumanApprovalToken(BaseStrictModel):
    """Signed token validating explicit human-in-the-loop approval."""
    token_id: str = Field(..., description="Unique approval token UUID.")
    user_id: str = Field(..., description="Approving user ID.")
    action_type: str = Field(..., description="Approved action payload type.")
    payload_hash: str = Field(..., description="SHA-256 hash of confirmed payload.")
    issued_at: float = Field(..., description="Unix timestamp of issuance.")
    expires_at: float = Field(..., description="Unix timestamp of expiration.")
    signature: str = Field(..., description="HMAC-SHA256 signature validating gate approval.")


class UserSettings(BaseStrictModel):
    """User profile and energy settings."""
    user_id: str = Field(..., description="User unique identifier.")
    email: str = Field(..., description="User Google Account email.")
    chronotype: Chronotype = Field(..., description="User diurnal chronotype profile.")
    max_daily_focus_hours: float = Field(default=6.0, ge=1.0, le=12.0, description="Daily focus time budget in hours.")


class EveningReflection(BaseStrictModel):
    """Evening shutdown reflection and metrics payload."""
    user_id: str = Field(..., description="User identifier.")
    date: str = Field(..., description="Date string YYYY-MM-DD.")
    fatigue_score: int = Field(..., ge=1, le=10, description="Evening self-reported fatigue score.")
    completed_tasks_count: int = Field(..., ge=0, description="Number of completed project tasks.")
    velocity_score: float = Field(..., ge=0.0, description="Daily execution velocity metric.")
    reflection_notes: Optional[str] = Field(None, description="Optional qualitative reflection notes.")


class InvocationContext(BaseStrictModel):
    """Session state context payload passed through ADK turns."""
    user_id: str = Field(..., description="Active user ID.")
    bearer_token: str = Field(..., description="OAuth 2.0 Access Token.")
    workflow: WorkflowType = Field(..., description="Current active workflow.")
    turn_index: int = Field(default=0, ge=0, description="Turn index within session.")
    active_state: Dict[str, Any] = Field(default_factory=dict, description="State parameters persistent across turns.")
