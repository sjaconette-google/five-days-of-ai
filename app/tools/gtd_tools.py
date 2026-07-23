"""GTD and Workload Focus agent tools catalog with Google-style docstrings and guided error handling."""


import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.models.domain import (
    GmailMessage,
    GTDInboxDecision,
    TriageToolContract,
    CapacityPlanningContract,
    DailyCommitmentPlan,
    CalendarFocusBlock,
    GTDActionType,
)
from app.services.workspace_service import WorkspaceService
from app.services.dlp_service import DLPService
from app.telemetry.logging import log_tool_intent, log_tool_outcome, logger


class GTDAgentTools:
    """Catalog of tools exposed to specialized ADK agents for Workspace operations and planning."""

    workspace_service: WorkspaceService
    dlp_service: DLPService

    def __init__(self, bearer_token: Optional[str] = None, mock_mode: bool = True) -> None:
        self.workspace_service: WorkspaceService = WorkspaceService(bearer_token=bearer_token, mock_mode=mock_mode)
        self.dlp_service: DLPService = DLPService()

    def fetch_unprocessed_inbox(self, user_id: str, limit: int = 10) -> List[GmailMessage]:
        """Scans unread inbox messages for interactive triage walkthrough, sanitizing PII content.

        Args:
            user_id: Unique user identifier for session execution context.
            limit: Maximum number of unread email messages to retrieve (default: 10).

        Returns:
            List[GmailMessage]: A list of sanitized Gmail message items.

        Raises:
            RuntimeError: If Google Workspace API call fails due to invalid or expired OAuth tokens.
        """
        start_time: float = time.time()
        log_tool_intent("fetch_unprocessed_inbox", user_id, {"limit": limit})

        try:
            raw_messages: List[GmailMessage] = self.workspace_service.fetch_unprocessed_inbox(limit=limit)
            sanitized_messages: List[GmailMessage] = []
            msg: GmailMessage
            for msg in raw_messages:
                sanitized_snippet: str = self.dlp_service.redact_pii(msg.snippet)
                sanitized_body: str = self.dlp_service.redact_pii(msg.body_text)
                sanitized_messages.append(
                    GmailMessage(
                        id=msg.id,
                        thread_id=msg.thread_id,
                        sender=msg.sender,
                        recipient=msg.recipient,
                        subject=msg.subject,
                        snippet=sanitized_snippet,
                        body_text=sanitized_body,
                        received_at=msg.received_at,
                    )
                )

            duration: float = (time.time() - start_time) * 1000
            log_tool_outcome("fetch_unprocessed_inbox", user_id, "SUCCESS", duration, {"count": len(sanitized_messages)})
            return sanitized_messages

        except Exception as e:
            duration: float = (time.time() - start_time) * 1000
            log_tool_outcome("fetch_unprocessed_inbox", user_id, "ERROR", duration, {"error": str(e)})
            logger.error("guided_error_handling_fetch_inbox", user_id=user_id, error=str(e))
            # Guided error return instructing agent/user on recovery
            raise RuntimeError(
                f"OAuth Token Expired or Invalid Workspace Permissions. Guided Recovery: Please trigger re-authentication via /auth/login. Details: {e}"
            )

    def apply_triage_decision(self, contract: TriageToolContract, user_id: str = "user_default") -> Dict[str, Any]:
        """Executes an approved GTD triage decision across Gmail and Google Tasks.

        Args:
            contract: Validated TriageToolContract containing message_id, action_type, and optional target project.
            user_id: Unique user identifier.

        Returns:
            Dict[str, Any]: Status dictionary containing message_id, action_applied, and generated google_task_id.

        Raises:
            RuntimeError: If Workspace API mutation fails.
        """
        start_time: float = time.time()
        log_tool_intent("apply_triage_decision", user_id, contract.model_dump())

        try:
            result: Dict[str, Any] = self.workspace_service.apply_triage_decision(
                message_id=contract.message_id,
                gtd_action=contract.action_type,
                target_project_id=contract.target_project_id,
                next_action_title=contract.next_action_title,
            )
            duration: float = (time.time() - start_time) * 1000
            log_tool_outcome("apply_triage_decision", user_id, "SUCCESS", duration, result)
            return result
        except Exception as e:
            duration: float = (time.time() - start_time) * 1000
            log_tool_outcome("apply_triage_decision", user_id, "ERROR", duration, {"error": str(e)})
            raise RuntimeError(f"Failed to execute triage decision. Guided Recovery: Verify Google Tasks access. Error: {e}")

    def generate_focus_plan(self, contract: CapacityPlanningContract, date_str: str = "2026-07-23") -> DailyCommitmentPlan:
        """Matches task commitments against user fatigue score, chronotype, and free-busy capacity.

        Optimization & Capacity Rules:
            - Fatigue >= 7 caps total focus block duration at 90 minutes max per block.
            - Total task duration is trimmed to fit within available free calendar capacity.
            - Composition: Exactly 1 P0 Frog task + 3 to 5 supporting tasks.

        Args:
            contract: Validated CapacityPlanningContract with user_id, fatigue score (1-10), P0 frog task ID, and support task IDs.
            date_str: Target planning date ISO format (YYYY-MM-DD).

        Returns:
            DailyCommitmentPlan: Structured capacity plan ready for user review.
        """
        start_time: float = time.time()
        log_tool_intent("generate_focus_plan", contract.user_id, contract.model_dump())

        # Query available free capacity from Workspace Service
        available_mins: int = self.workspace_service.fetch_free_busy_capacity(date_str)

        # Capacity logic: Scale focus duration per block based on fatigue score
        max_block_mins: int = 90 if contract.current_fatigue_score >= 7 else 120
        frog_duration: int = min(60, max_block_mins)
        support_duration_per_item: int = 30 if contract.current_fatigue_score >= 7 else 45

        # Trim lower-priority support tasks if total duration exceeds capacity
        fitted_support_ids: List[str] = []
        accumulated_duration: int = frog_duration

        task_id: str
        for task_id in contract.support_task_ids:
            if accumulated_duration + support_duration_per_item <= available_mins and len(fitted_support_ids) < 5:
                fitted_support_ids.append(task_id)
                accumulated_duration += support_duration_per_item
            else:
                logger.info("auto_trimmed_support_task_overcapacity", task_id=task_id, available=available_mins)

        # Construct scheduled focus blocks
        focus_blocks: List[CalendarFocusBlock] = []
        cur_time: datetime = datetime.fromisoformat(f"{date_str}T09:00:00")
        
        # Add Frog Task block
        end_time: datetime = cur_time + timedelta(minutes=frog_duration)
        focus_blocks.append(
            CalendarFocusBlock(
                title=f"Primary Outcome (P0 Frog): Task {contract.frog_task_id}",
                start_time=cur_time.isoformat() + "Z",
                end_time=end_time.isoformat() + "Z",
                task_id=contract.frog_task_id,
            )
        )
        cur_time = end_time + timedelta(minutes=15)  # 15 min rest buffer

        # Add Support Task blocks
        supp_id: str
        for supp_id in fitted_support_ids:
            end_time = cur_time + timedelta(minutes=support_duration_per_item)
            focus_blocks.append(
                CalendarFocusBlock(
                    title=f"Support Action: Task {supp_id}",
                    start_time=cur_time.isoformat() + "Z",
                    end_time=end_time.isoformat() + "Z",
                    task_id=supp_id,
                )
            )
            cur_time = end_time + timedelta(minutes=15)

        alignment_notes: str = (
            f"Plan fitted for fatigue score {contract.current_fatigue_score}/10. "
            f"Max block cap: {max_block_mins}m. Total scheduled: {accumulated_duration}m / {available_mins}m available capacity."
        )

        plan: DailyCommitmentPlan = DailyCommitmentPlan(
            plan_date=date_str,
            frog_task_id=contract.frog_task_id,
            support_task_ids=fitted_support_ids,
            total_estimated_duration_minutes=accumulated_duration,
            available_capacity_minutes=available_mins,
            alignment_notes=alignment_notes,
            focus_blocks=focus_blocks,
        )

        duration: float = (time.time() - start_time) * 1000
        log_tool_outcome("generate_focus_plan", contract.user_id, "SUCCESS", duration, {"total_mins": accumulated_duration})
        return plan

    def schedule_focus_blocks(self, plan: DailyCommitmentPlan, user_id: str = "user_default") -> List[Dict[str, Any]]:
        """Schedules focus time blocks exclusively on secondary sub-calendar 'EF Focus Planner'.

        Args:
            plan: DailyCommitmentPlan payload confirmed by the user.
            user_id: Target user ID.

        Returns:
            List[Dict[str, Any]]: List of created calendar event details.
        """
        start_time: float = time.time()
        log_tool_intent("schedule_focus_blocks", user_id, {"plan_date": plan.plan_date})

        try:
            results: List[Dict[str, Any]] = self.workspace_service.schedule_focus_blocks(plan)
            duration: float = (time.time() - start_time) * 1000
            log_tool_outcome("schedule_focus_blocks", user_id, "SUCCESS", duration, {"created_count": len(results)})
            return results
        except Exception as e:
            duration: float = (time.time() - start_time) * 1000
            log_tool_outcome("schedule_focus_blocks", user_id, "ERROR", duration, {"error": str(e)})
            raise RuntimeError(f"Calendar Focus Scheduling failed. Guided Error Recovery: {e}")

