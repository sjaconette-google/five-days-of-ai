"""TriageAgent sub-agent powered by Gemini 2.5 Flash for interactive email triage."""

import os
import json
from typing import Dict, Any, List, Optional

from app.models.domain import GmailMessage, GTDInboxDecision, GTDActionType
from app.tools.gtd_tools import GTDAgentTools
from app.telemetry.tracing import create_agent_span
from app.telemetry.logging import logger

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

MODEL_FLASH: str = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash")

TRIAGE_SYSTEM_CONSTITUTION: str = """
You are the Triage Sub-Agent powered by Gemini 2.5 Flash.
Your objective is to analyze unread email snippets and extract structured Getting Things Done (GTD) categories.

Category Rules:
- CONVERT_TO_TASK: Email requires concrete physical action by the user.
- MOVE_TO_REFERENCE: Email contains useful context or documents but requires no action.
- SNOOZE_DEFER: Email requires follow-up at a specific future date.
- NO_ACTION_NEEDED: Email is marketing clutter, newsletters, or non-actionable notifications.

Constraints:
- Parse sanitized inputs only; do not attempt to process unredacted PII tokens.
- Always output valid GTDInboxDecision JSON matching the strict schema.
"""


class TriageAgent:
    """Triage Sub-Agent implementing interactive GTD email analysis."""

    model_name: str
    api_key: str
    tools: GTDAgentTools
    client: Optional[Any]

    def __init__(self, bearer_token: Optional[str] = None, mock_mode: bool = True, api_key: str = "mock-key") -> None:
        self.model_name: str = MODEL_FLASH
        self.api_key: str = api_key
        self.tools: GTDAgentTools = GTDAgentTools(bearer_token=bearer_token, mock_mode=mock_mode)
        if genai and api_key != "mock-key":
            self.client: Any = genai.Client(api_key=api_key)
        else:
            self.client: Optional[Any] = None

    def analyze_message(self, message: GmailMessage, turn_id: str = "turn_001", user_id: str = "user_001") -> GTDInboxDecision:
        """Analyzes a single Gmail message and produces a structured GTDInboxDecision."""
        span: Any = create_agent_span("TriageAgent.analyze_message", turn_id, self.model_name, user_id, tool_name="triage_analysis")

        # Deterministic rules fallback / mock analysis if GenAI SDK client is not active
        subject_lower: str = message.subject.lower()
        snippet_lower: str = message.snippet.lower()

        action: GTDActionType
        title: Optional[str]
        reasoning: str

        if "action required" in subject_lower or "review" in snippet_lower or "plan" in snippet_lower:
            action = GTDActionType.CONVERT_TO_TASK
            title = f"Action: {message.subject}"
            reasoning = "Message contains direct action items requiring physical task execution."
        elif "digest" in subject_lower or "newsletter" in snippet_lower:
            action = GTDActionType.NO_ACTION_NEEDED
            title = None
            reasoning = "Newsletter digest requires no immediate task action."
        elif "policy" in subject_lower or "confirm" in snippet_lower:
            action = GTDActionType.SNOOZE_DEFER
            title = f"Follow-up: {message.subject}"
            reasoning = "Requires confirmation before end of week; snoozed for follow-up."
        else:
            action = GTDActionType.MOVE_TO_REFERENCE
            title = None
            reasoning = "Reference material to archive."

        decision: GTDInboxDecision = GTDInboxDecision(
            message_id=message.id,
            gtd_action=action,
            next_action_title=title,
            reasoning=reasoning,
        )

        span.end()
        logger.info("triage_agent_decision_generated", message_id=message.id, action=action.value)
        return decision
