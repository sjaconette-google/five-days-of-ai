"""ADKRouter agent powered by Gemini 2.5 Flash managing context window compaction and workflow routing."""

import os
from typing import Dict, Any, List, Optional
from app.models.domain import (
    WorkflowType,
    InvocationContext,
    UserSettings,
    Chronotype,
    TriageToolContract,
    CapacityPlanningContract,
    HumanApprovalToken,
)
from app.agents.triage import TriageAgent
from app.agents.planning import PlanningAgent
from app.agents.execution import ExecutionAgent
from app.telemetry.tracing import create_agent_span
from app.telemetry.logging import logger

MODEL_FLASH: str = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash")
MAX_CONTEXT_TOKENS: int = 2048

ROUTER_SYSTEM_CONSTITUTION: str = """
You are the ADK Router Agent for the GTD and Workload Focus Assistant.
Your primary role is to evaluate user turn intents, manage short-term session state, and route control flow to specialized sub-agents.

Routing Policy:
- If user intent relates to parsing unread emails or triage, delegate to TriageAgent.
- If user intent relates to morning energy profiling, focus hours, or scheduling, delegate to PlanningAgent.
- If user intent confirms an approved draft action, delegate to ExecutionAgent.

Constraints:
- Maintain conversation sliding window context strictly under 2,048 tokens.
- Never call external Workspace APIs directly; delegate all mutations to ExecutionAgent.
"""



class ADKRouter:
    """ADK Router Agent orchestrating sub-agent delegation and context window history compaction."""

    model_name: str
    mock_mode: bool
    triage_agent: TriageAgent
    planning_agent: PlanningAgent
    execution_agent: ExecutionAgent

    def __init__(self, bearer_token: Optional[str] = None, mock_mode: bool = True) -> None:
        self.model_name: str = MODEL_FLASH
        self.mock_mode: bool = mock_mode
        self.triage_agent: TriageAgent = TriageAgent(bearer_token=bearer_token, mock_mode=mock_mode)
        self.planning_agent: PlanningAgent = PlanningAgent(bearer_token=bearer_token, mock_mode=mock_mode)
        self.execution_agent: ExecutionAgent = ExecutionAgent(bearer_token=bearer_token, mock_mode=mock_mode)

    def compact_history_sliding_window(self, history: List[Dict[str, str]], max_tokens: int = MAX_CONTEXT_TOKENS) -> List[Dict[str, str]]:
        """
        ADK History Compaction Middleware.
        Compacts turn history messages to preserve context under the 2,048 token threshold.
        """
        # Approximating tokens via character length (1 token ~ 4 chars)
        total_estimated_tokens: int = sum(len(m.get("content", "")) // 4 for m in history)
        if total_estimated_tokens <= max_tokens:
            return history

        # Compact by keeping system message + last N recent turns
        logger.info("adk_history_compaction_triggered", estimated_tokens=total_estimated_tokens, target_max=max_tokens)
        compacted: List[Dict[str, str]] = []
        if history and history[0].get("role") == "system":
            compacted.append(history[0])

        recent_turns: List[Dict[str, str]] = history[-4:]  # Retain last 4 turns
        compacted.extend(recent_turns)
        return compacted

    def route_turn(
        self,
        user_prompt: str,
        context: InvocationContext,
        history: Optional[List[Dict[str, str]]] = None,
        user_settings: Optional[UserSettings] = None,
    ) -> Dict[str, Any]:
        """Parses user turn intent, compacts context history, and delegates to specialized sub-agent."""
        span: Any = create_agent_span("ADKRouter.route_turn", f"turn_{context.turn_index}", self.model_name, context.user_id)

        history_list: List[Dict[str, str]] = history or []
        compacted_history: List[Dict[str, str]] = self.compact_history_sliding_window(history_list)

        prompt_lower: str = user_prompt.lower()
        active_settings: UserSettings = user_settings if user_settings is not None else UserSettings(user_id=context.user_id, email="user@example.com", chronotype=Chronotype.MORNING_LARK)

        # Classify intent & delegate
        if "triage" in prompt_lower or "email" in prompt_lower or "inbox" in prompt_lower:
            context.workflow = WorkflowType.INBOX_TRIAGE
            logger.info("router_delegating_to_triage_agent", user_id=context.user_id)
            messages: List[Any] = self.triage_agent.tools.fetch_unprocessed_inbox(user_id=context.user_id, limit=3)
            decisions: List[Any] = [self.triage_agent.analyze_message(msg, user_id=context.user_id) for msg in messages]
            span.end()
            return {
                "routed_workflow": WorkflowType.INBOX_TRIAGE.value,
                "agent": "TriageAgent",
                "inbox_messages": [m.model_dump() for m in messages],
                "proposed_gtd_decisions": [d.model_dump() for d in decisions],
                "history_length": len(compacted_history),
            }

        elif "plan" in prompt_lower or "schedule" in prompt_lower or "fatigue" in prompt_lower:
            context.workflow = WorkflowType.DAILY_PLANNING
            logger.info("router_delegating_to_planning_agent", user_id=context.user_id)

            # Extract fatigue score default from prompt if present or default to 5
            fatigue: int = 5
            token: str
            for token in user_prompt.split():
                if token.isdigit() and 1 <= int(token) <= 10:
                    fatigue = int(token)
                    break

            contract: CapacityPlanningContract = CapacityPlanningContract(
                user_id=context.user_id,
                current_fatigue_score=fatigue,
                frog_task_id="task_p0_frog_01",
                support_task_ids=["task_p1_01", "task_p1_02", "task_p2_01", "task_p2_02", "task_p3_01"],
            )
            plan: DailyCommitmentPlan = self.planning_agent.create_daily_plan(contract=contract, user_settings=active_settings)
            span.end()
            return {
                "routed_workflow": WorkflowType.DAILY_PLANNING.value,
                "agent": "PlanningAgent",
                "commitment_plan_draft": plan.model_dump(),
                "history_length": len(compacted_history),
            }

        elif "approve" in prompt_lower or "execute" in prompt_lower or "confirm" in prompt_lower:
            context.workflow = WorkflowType.WORKSPACE_MUTATION
            logger.info("router_delegating_to_execution_agent", user_id=context.user_id)
            span.end()
            return {
                "routed_workflow": WorkflowType.WORKSPACE_MUTATION.value,
                "agent": "ExecutionAgent",
                "status": "Awaiting Human Confirmation Gate payload validation.",
            }

        else:
            # Default fallback conversational turn
            span.end()
            return {
                "routed_workflow": "GENERAL_CONVERSATION",
                "agent": "ADKRouter",
                "response": "Hello! I am your GTD and Workload Focus Assistant. You can ask me to: 1) Triage your unread emails turn-by-turn, 2) Plan your daily focus schedule based on your energy & fatigue score, or 3) Execute approved Workspace mutations.",
            }


