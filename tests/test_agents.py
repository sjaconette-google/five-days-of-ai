"""Unit tests for ADK Router, sub-agents, and Human Confirmation Gate signing."""

try:
    import pytest
except ImportError:
    pytest = None

from app.models.domain import (
    InvocationContext,
    WorkflowType,
    UserSettings,
    Chronotype,
    TriageToolContract,
    GTDActionType,
)
from app.agents.router import ADKRouter
from app.agents.execution import ExecutionAgent
from app.services.auth_service import AuthService


def test_adk_router_triage_delegation():
    router = ADKRouter(mock_mode=True)
    context = InvocationContext(user_id="u100", bearer_token="token_mock", workflow=WorkflowType.DAILY_PLANNING)
    res = router.route_turn("Please help me triage my unread inbox", context=context)

    assert res["routed_workflow"] == WorkflowType.INBOX_TRIAGE.value
    assert res["agent"] == "TriageAgent"
    assert len(res["proposed_gtd_decisions"]) > 0


def test_adk_router_planning_delegation():
    router = ADKRouter(mock_mode=True)
    context = InvocationContext(user_id="u100", bearer_token="token_mock", workflow=WorkflowType.DAILY_PLANNING)
    res = router.route_turn("I have fatigue score 7 today, plan my schedule", context=context)

    assert res["routed_workflow"] == WorkflowType.DAILY_PLANNING.value
    assert res["agent"] == "PlanningAgent"
    assert "commitment_plan_draft" in res


def test_adk_history_compaction():
    router = ADKRouter(mock_mode=True)
    large_history = [{"role": "user", "content": "x" * 2000} for _ in range(10)]
    compacted = router.compact_history_sliding_window(large_history, max_tokens=1000)

    assert len(compacted) < len(large_history)


def test_human_confirmation_gate_security():
    execution_agent = ExecutionAgent(mock_mode=True)
    contract = TriageToolContract(message_id="msg_99", action_type=GTDActionType.CONVERT_TO_TASK, next_action_title="Action")
    user_id = "user_gate_test"

    # 1. Reject execution without valid token
    invalid_token = AuthService.issue_human_approval_token(user_id, "OTHER_ACTION", contract.model_dump())
    if pytest is not None:
        with pytest.raises(PermissionError):
            execution_agent.execute_triage_mutation(invalid_token, contract, user_id=user_id)
    else:
        raised = False
        try:
            execution_agent.execute_triage_mutation(invalid_token, contract, user_id=user_id)
        except PermissionError:
            raised = True
        assert raised, "Expected PermissionError for invalid approval token"


    # 2. Accept execution with valid signed token matching payload
    valid_token = AuthService.issue_human_approval_token(user_id, "TRIAGE_MUTATION", contract.model_dump())
    res = execution_agent.execute_triage_mutation(valid_token, contract, user_id=user_id)
    assert res["status"] == "SUCCESS"


def test_async_memory_operations_and_background_tasks():
    import asyncio
    try:
        from fastapi import BackgroundTasks
        bg_tasks = BackgroundTasks()
        bg_tasks.add_task(async_save_memory_turn, "u_async", 1, "test prompt", "DAILY_PLANNING")
    except ImportError:
        bg_tasks = None

    from app.services.db_service import async_save_memory_turn, async_save_evening_reflection
    from app.models.domain import EveningReflection

    reflection = EveningReflection(user_id="u_async", date="2026-07-23", completed_tasks_count=3, velocity_score=8, fatigue_score=4)

    # Execute async tasks
    asyncio.run(async_save_memory_turn("u_async", 1, "test prompt", "DAILY_PLANNING"))
    asyncio.run(async_save_evening_reflection("u_async", reflection))


