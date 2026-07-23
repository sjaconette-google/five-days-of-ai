"""Unit tests for capacity planning multi-constraint matching and energy scaling."""

try:
    import pytest
except ImportError:
    pytest = None

from app.models.domain import CapacityPlanningContract, UserSettings, Chronotype
from app.tools.gtd_tools import GTDAgentTools
from app.agents.planning import PlanningAgent


def test_capacity_matching_low_fatigue():
    tools = GTDAgentTools(mock_mode=True)
    contract = CapacityPlanningContract(
        user_id="user_test_01",
        current_fatigue_score=3,
        frog_task_id="p0_frog",
        support_task_ids=["p1_supp_01", "p1_supp_02", "p1_supp_03", "p1_supp_04", "p1_supp_05"],
    )
    plan = tools.generate_focus_plan(contract=contract)

    assert plan.frog_task_id == "p0_frog"
    assert len(plan.support_task_ids) <= 5
    assert plan.total_estimated_duration_minutes <= plan.available_capacity_minutes


def test_capacity_matching_high_fatigue_scaling():
    tools = GTDAgentTools(mock_mode=True)
    # High fatigue score (8/10) should cap block durations and trim tasks
    contract = CapacityPlanningContract(
        user_id="user_test_02",
        current_fatigue_score=8,
        frog_task_id="p0_frog",
        support_task_ids=["supp_01", "supp_02", "supp_03", "supp_04", "supp_05"],
    )
    plan = tools.generate_focus_plan(contract=contract)

    assert "Max block cap: 90m" in plan.alignment_notes
    assert plan.total_estimated_duration_minutes <= plan.available_capacity_minutes


def test_planning_agent_chronotype_alignment():
    agent = PlanningAgent(mock_mode=True)
    settings = UserSettings(user_id="user_lark", email="lark@co.com", chronotype=Chronotype.MORNING_LARK)
    contract = CapacityPlanningContract(
        user_id="user_lark",
        current_fatigue_score=4,
        frog_task_id="p0_frog",
        support_task_ids=["supp_01", "supp_02"],
    )
    plan = agent.create_daily_plan(contract=contract, user_settings=settings)

    assert "Chronotype: MORNING_LARK" in plan.alignment_notes
    assert len(plan.focus_blocks) >= 1
