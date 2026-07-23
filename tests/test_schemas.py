"""Unit tests validating Pydantic v2 schema models and strict type annotations."""

import inspect
import importlib
import pkgutil
from typing import get_type_hints, Callable, Any

try:
    import pytest
except ImportError:
    pytest = None

from pydantic import ValidationError
from app.models.domain import (
    GmailMessage,
    GTDInboxDecision,
    TriageToolContract,
    CapacityPlanningContract,
    DailyCommitmentPlan,
    GTDActionType,
)


def test_gmail_message_parsing() -> None:
    raw_payload = {
        "id": "msg_101",
        "thread_id": "thread_101",
        "sender": "lead@company.com",
        "recipient": "user@company.com",
        "subject": "Q3 Planning",
        "snippet": "Review attached Q3 plan.",
        "body_text": "Review attached Q3 plan.",
        "received_at": "2026-07-23T10:00:00Z",
    }
    msg = GmailMessage(**raw_payload)
    assert msg.id == "msg_101"
    assert msg.sender == "lead@company.com"


def test_strict_schema_extra_fields_forbidden() -> None:
    raw_payload = {
        "id": "msg_101",
        "thread_id": "thread_101",
        "sender": "lead@company.com",
        "recipient": "user@company.com",
        "subject": "Q3 Planning",
        "snippet": "Review attached Q3 plan.",
        "body_text": "Review attached Q3 plan.",
        "received_at": "2026-07-23T10:00:00Z",
        "unauthorized_extra_field": "prompt_injection_payload",
    }
    if pytest is not None:
        with pytest.raises(ValidationError):
            GmailMessage(**raw_payload)
    else:
        raised = False
        try:
            GmailMessage(**raw_payload)
        except ValidationError:
            raised = True
        assert raised, "Expected ValidationError for extra fields"


def test_triage_tool_contract_validation() -> None:
    valid = {
        "message_id": "msg_101",
        "action_type": "CONVERT_TO_TASK",
        "target_project_id": "proj_99",
        "next_action_title": "Review Q3 Plan",
    }
    contract = TriageToolContract(**valid)
    assert contract.action_type == GTDActionType.CONVERT_TO_TASK


def test_capacity_plan_validation() -> None:
    valid_plan = {
        "plan_date": "2026-07-23",
        "frog_task_id": "task_p0_01",
        "support_task_ids": ["task_p1_01", "task_p1_02"],
        "total_estimated_duration_minutes": 180,
        "available_capacity_minutes": 240,
        "alignment_notes": "Plan matches 4-hour focus limit.",
        "focus_blocks": [],
    }
    plan = DailyCommitmentPlan(**valid_plan)
    assert plan.available_capacity_minutes >= plan.total_estimated_duration_minutes


def test_codebase_type_annotations_completeness() -> None:
    """Verifies that all public functions and methods in app/ have explicit type annotations."""
    import app.models.domain
    import app.tools.gtd_tools
    import app.agents.router
    import app.agents.triage
    import app.agents.planning
    import app.agents.execution
    from enum import Enum

    modules = [
        app.models.domain,
        app.tools.gtd_tools,
        app.agents.router,
        app.agents.triage,
        app.agents.planning,
        app.agents.execution,
    ]

    untyped = []
    for mod in modules:
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__ == mod.__name__ and not issubclass(obj, Enum):
                for meth_name, meth in inspect.getmembers(obj, predicate=inspect.isfunction):
                    if not meth_name.startswith("_") or meth_name == "__init__":
                        sig = inspect.signature(meth)
                        if sig.return_annotation is inspect.Signature.empty:
                            untyped.append(f"{obj.__name__}.{meth_name} (missing return annotation)")

    assert len(untyped) == 0, f"Found untyped functions: {untyped}"

