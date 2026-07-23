"""PlanningAgent sub-agent powered by Gemini 2.5 Pro for daily energy-budget focus scheduling."""

import os
from typing import List, Dict, Any, Optional
from app.models.domain import (
    CapacityPlanningContract,
    DailyCommitmentPlan,
    Chronotype,
    UserSettings,
)
from app.tools.gtd_tools import GTDAgentTools
from app.telemetry.tracing import create_agent_span
from app.telemetry.logging import logger

MODEL_PRO: str = os.getenv("GEMINI_PRO_MODEL", "gemini-2.5-pro")

PLANNING_SYSTEM_CONSTITUTION: str = """
You are the Planning Sub-Agent powered by Gemini 2.5 Pro.
Your objective is to generate capacity-fitted daily focus plans that prevent decision fatigue and optimize high-focus productivity windows.

Optimization Rules:
- User Fatigue Score (1-10): Scale focus block duration inversely with fatigue (Fatigue >= 7 caps focus blocks at 90 mins max).
- Chronotype: Schedule high-focus tasks during morning peak for MORNING_LARK; late afternoon for NIGHT_OWL.
- Commitment Composition: Select exactly ONE primary outcome task (P0 Frog) and 3 to 5 support tasks.
- Overcapacity Rule: If total task duration exceeds free calendar capacity, trim lower-priority support tasks until total duration fits within free capacity.
"""



class PlanningAgent:
    """Planning Sub-Agent generating capacity plans matching energy budgets and calendar availability."""

    model_name: str
    tools: GTDAgentTools

    def __init__(self, bearer_token: Optional[str] = None, mock_mode: bool = True) -> None:
        self.model_name: str = MODEL_PRO
        self.tools: GTDAgentTools = GTDAgentTools(bearer_token=bearer_token, mock_mode=mock_mode)


    def create_daily_plan(
        self,
        contract: CapacityPlanningContract,
        user_settings: UserSettings,
        date_str: str = "2026-07-23",
        turn_id: str = "turn_002",
    ) -> DailyCommitmentPlan:
        """Generates a fitted DailyCommitmentPlan matching fatigue score, chronotype, and calendar capacity."""
        span: Any = create_agent_span("PlanningAgent.create_daily_plan", turn_id, self.model_name, contract.user_id, tool_name="generate_focus_plan")

        plan: DailyCommitmentPlan = self.tools.generate_focus_plan(contract=contract, date_str=date_str)

        # Enhance alignment notes with chronotype specifics
        chronotype_note: str = f"Chronotype: {user_settings.chronotype.value} (Peak focus aligned)."
        plan.alignment_notes = f"{chronotype_note} {plan.alignment_notes}"

        span.end()
        logger.info(
            "planning_agent_plan_generated",
            user_id=contract.user_id,
            frog=plan.frog_task_id,
            support_count=len(plan.support_task_ids),
        )
        return plan
