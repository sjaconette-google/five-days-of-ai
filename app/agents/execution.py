"""ExecutionAgent sub-agent powered by Gemini 2.5 Flash with Human-in-the-Loop gate verification."""

import os
from typing import Dict, Any, List, Optional
from app.models.domain import HumanApprovalToken, TriageToolContract, DailyCommitmentPlan
from app.tools.gtd_tools import GTDAgentTools
from app.services.auth_service import AuthService
from app.telemetry.tracing import create_agent_span
from app.telemetry.logging import logger

MODEL_FLASH: str = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash")

EXECUTION_SYSTEM_CONSTITUTION: str = """
You are the Execution Sub-Agent powered by Gemini 2.5 Flash.
Your objective is to execute approved workspace mutations against Gmail, Google Tasks, and Google Calendar.

Safety Protocol:
- Verify that the target payload bears a valid HumanApprovalToken signed by the Human Confirmation Gate.
- Reject any execution request lacking explicit user confirmation.
- Write focus blocks exclusively to secondary sub-calendar "EF Focus Planner".
"""


class ExecutionAgent:
    """Execution Sub-Agent operating behind the Human Confirmation Gate."""

    model_name: str
    tools: GTDAgentTools

    def __init__(self, bearer_token: Optional[str] = None, mock_mode: Optional[bool] = True) -> None:
        self.model_name: str = MODEL_FLASH
        self.tools: GTDAgentTools = GTDAgentTools(bearer_token=bearer_token, mock_mode=mock_mode)

    def execute_triage_mutation(
        self,
        approval_token: HumanApprovalToken,
        contract: TriageToolContract,
        user_id: str,
        turn_id: str = "turn_exec_01",
    ) -> Dict[str, Any]:
        """Executes triage mutation only after validating HumanApprovalToken signature."""
        span: Any = create_agent_span("ExecutionAgent.execute_triage_mutation", turn_id, self.model_name, user_id, tool_name="apply_triage_decision")

        # Verify gate approval signature & payload hash
        payload_dict: Dict[str, Any] = contract.model_dump()
        is_valid: bool = AuthService.verify_human_approval_token(approval_token, user_id, "TRIAGE_MUTATION", payload_dict)

        if not is_valid:
            span.end()
            logger.error("execution_gate_rejected_invalid_approval_token", user_id=user_id, token_id=approval_token.token_id)
            raise PermissionError("Human Confirmation Gate Rejection: Missing or invalid HumanApprovalToken signature.")

        result: Dict[str, Any] = self.tools.apply_triage_decision(contract, user_id=user_id)
        span.end()
        logger.info("execution_agent_triage_mutation_success", user_id=user_id, message_id=contract.message_id)
        return result

    def execute_schedule_mutation(
        self,
        approval_token: HumanApprovalToken,
        plan: DailyCommitmentPlan,
        user_id: str,
        turn_id: str = "turn_exec_02",
    ) -> List[Dict[str, Any]]:
        """Schedules focus blocks on secondary sub-calendar 'EF Focus Planner' after gate approval verification."""
        span: Any = create_agent_span("ExecutionAgent.execute_schedule_mutation", turn_id, self.model_name, user_id, tool_name="schedule_focus_blocks")

        payload_dict: Dict[str, Any] = plan.model_dump()
        is_valid: bool = AuthService.verify_human_approval_token(approval_token, user_id, "SCHEDULE_MUTATION", payload_dict)

        if not is_valid:
            span.end()
            logger.error("execution_gate_rejected_schedule_token", user_id=user_id, token_id=approval_token.token_id)
            raise PermissionError("Human Confirmation Gate Rejection: Missing or invalid HumanApprovalToken signature.")

        results: List[Dict[str, Any]] = self.tools.schedule_focus_blocks(plan, user_id=user_id)
        span.end()
        logger.info("execution_agent_schedule_mutation_success", user_id=user_id, blocks_count=len(results))
        return results

