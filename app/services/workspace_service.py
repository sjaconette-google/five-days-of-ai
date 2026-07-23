"""Google Workspace APIs service client wrapper for Gmail, Tasks, and Calendar."""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.models.domain import GmailMessage, GTDActionType, DailyCommitmentPlan, CalendarFocusBlock
from app.telemetry.logging import logger

try:
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
except ImportError:
    build = None
    Credentials = None


FOCUS_CALENDAR_NAME: str = "EF Focus Planner"


class WorkspaceService:
    """Service wrapper for interacting with Google Workspace APIs."""

    bearer_token: Optional[str]
    mock_mode: bool
    _gmail: Optional[Any]
    _tasks: Optional[Any]
    _calendar: Optional[Any]

    def __init__(self, bearer_token: Optional[str] = None, mock_mode: Optional[bool] = None) -> None:
        self.bearer_token = bearer_token
        if mock_mode is not None:
            self.mock_mode = mock_mode
        else:
            self.mock_mode = os.getenv("WORKSPACE_MOCK_MODE", "true").lower() == "true" or (not bearer_token)
        self._gmail = None
        self._tasks = None
        self._calendar = None

    def _init_clients(self) -> None:
        if not self.mock_mode and build and Credentials and self.bearer_token:
            creds: Any = Credentials(token=self.bearer_token)
            self._gmail = build("gmail", "v1", credentials=creds)
            self._tasks = build("tasks", "v1", credentials=creds)
            self._calendar = build("calendar", "v3", credentials=creds)

    def fetch_unprocessed_inbox(self, limit: int = 10) -> List[GmailMessage]:
        """Scans unread inbox messages for interactive triage walkthrough."""
        if self.mock_mode:
            logger.info("workspace_service_mock_fetch_inbox", count=limit)
            messages: List[GmailMessage] = [
                GmailMessage(
                    id="msg_101",
                    thread_id="thread_101",
                    sender="lead@company.com",
                    recipient="user@company.com",
                    subject="Q3 Architecture Planning & Review",
                    snippet="Please review the attached Q3 plan and outline key milestones by Friday.",
                    body_text="Hi, Please review the attached Q3 plan and outline key milestones by Friday. Thanks!",
                    received_at="2026-07-23T10:00:00Z",
                ),
                GmailMessage(
                    id="msg_102",
                    thread_id="thread_102",
                    sender="newsletter@techdigest.io",
                    recipient="user@company.com",
                    subject="Weekly AI Innovations Roundup #42",
                    snippet="Here is your weekly digest of top AI research papers.",
                    body_text="Here is your weekly digest of top AI research papers and framework releases.",
                    received_at="2026-07-23T08:30:00Z",
                ),
                GmailMessage(
                    id="msg_103",
                    thread_id="thread_103",
                    sender="hr@company.com",
                    recipient="user@company.com",
                    subject="Action Required: Open Enrollment Policy Confirmation",
                    snippet="Please confirm your 2026 health benefit selection by end of week.",
                    body_text="Important reminder: Open enrollment closes this Friday. Please log into the portal and confirm choices.",
                    received_at="2026-07-23T09:15:00Z",
                ),
            ]
            return messages[:limit]

        self._init_clients()
        try:
            results: Dict[str, Any] = self._gmail.users().messages().list(userId="me", q="is:unread label:INBOX", maxResults=limit).execute()
            messages_list: List[Dict[str, Any]] = results.get("messages", [])
            output: List[GmailMessage] = []
            for msg_item in messages_list:
                detail: Dict[str, Any] = self._gmail.users().messages().get(userId="me", id=msg_item["id"], format="full").execute()
                headers: Dict[str, str] = {h["name"].lower(): h["value"] for h in detail.get("payload", {}).get("headers", [])}
                output.append(
                    GmailMessage(
                        id=detail["id"],
                        thread_id=detail["threadId"],
                        sender=headers.get("from", "unknown"),
                        recipient=headers.get("to", "me"),
                        subject=headers.get("subject", "(No Subject)"),
                        snippet=detail.get("snippet", ""),
                        body_text=detail.get("snippet", ""),
                        received_at=datetime.utcnow().isoformat() + "Z",
                    )
                )
            return output
        except Exception as e:
            err: Exception = e
            logger.error("workspace_api_error_fetch_inbox", error=str(err))
            raise RuntimeError(f"Workspace Gmail API failed (OAuth token expired?): {err}")

    def apply_triage_decision(
        self,
        message_id: str,
        gtd_action: GTDActionType,
        target_project_id: Optional[str] = None,
        next_action_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes triage actions: Task creation, Gmail labeling/archive, or Defer/Snooze."""
        created_task_id: Optional[str] = None

        if gtd_action == GTDActionType.CONVERT_TO_TASK:
            title: str = next_action_title or "Process Email Action"
            created_task_id = self.create_google_task(title=title, project_id=target_project_id, notes=f"From Gmail ID: {message_id}")

        if self.mock_mode:
            logger.info("workspace_service_mock_triage_decision", message_id=message_id, action=gtd_action)
            res_mock: Dict[str, Any] = {
                "status": "SUCCESS",
                "message_id": message_id,
                "action_applied": gtd_action.value,
                "google_task_id": created_task_id or f"task_mock_{message_id}",
            }
            return res_mock

        self._init_clients()
        try:
            # Modify message labels (Archive / Mark Read)
            self._gmail.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD", "INBOX"]}
            ).execute()

            res_live: Dict[str, Any] = {
                "status": "SUCCESS",
                "message_id": message_id,
                "action_applied": gtd_action.value,
                "google_task_id": created_task_id,
            }
            return res_live
        except Exception as e:
            err_triage: Exception = e
            logger.error("workspace_api_error_triage_decision", error=str(err_triage))
            raise RuntimeError(f"Workspace Triage modification failed: {err_triage}")

    def create_google_task(self, title: str, project_id: Optional[str] = None, notes: Optional[str] = None) -> str:
        """Creates a Google Task item."""
        if self.mock_mode:
            mock_id: str = f"gtask_{hash(title) % 10000}"
            logger.info("workspace_service_mock_create_task", title=title, task_id=mock_id)
            return mock_id

        self._init_clients()
        tasklist_id: str = project_id or "@default"
        task_body: Dict[str, str] = {"title": title, "notes": notes or ""}
        result: Dict[str, Any] = self._tasks.tasks().insert(tasklist=tasklist_id, body=task_body).execute()
        created_id: str = str(result.get("id", ""))
        return created_id

    def fetch_free_busy_capacity(self, date_str: str) -> int:
        """Fetches available free calendar capacity in minutes for target day."""
        if self.mock_mode:
            # Default mock 240 minutes (4 hours) free focus capacity
            return 240

        self._init_clients()
        try:
            time_min: str = f"{date_str}T08:00:00Z"
            time_max: str = f"{date_str}T18:00:00Z"
            body: Dict[str, Any] = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": "primary"}],
            }
            res: Dict[str, Any] = self._calendar.freebusy().query(body=body).execute()
            busy_slots: List[Dict[str, Any]] = res.get("calendars", {}).get("primary", {}).get("busy", [])
            total_busy_mins: int = 0
            for slot in busy_slots:
                start: datetime = datetime.fromisoformat(slot["start"].replace("Z", "+00:00"))
                end: datetime = datetime.fromisoformat(slot["end"].replace("Z", "+00:00"))
                total_busy_mins += int((end - start).total_seconds() / 60)

            total_work_day_mins: int = 10 * 60  # 8am to 6pm
            available_capacity: int = max(0, total_work_day_mins - total_busy_mins)
            return available_capacity
        except Exception as e:
            err_fb: Exception = e
            logger.warning("workspace_api_error_free_busy_fallback", error=str(err_fb))
            return 240

    def get_or_create_secondary_focus_calendar(self) -> str:
        """Ensures dedicated 'EF Focus Planner' secondary sub-calendar exists to preserve primary calendar hygiene."""
        if self.mock_mode:
            return "secondary_ef_focus_cal_id"

        self._init_clients()
        try:
            calendar_list: Dict[str, Any] = self._calendar.calendarList().list().execute()
            cal_items: List[Dict[str, Any]] = calendar_list.get("items", [])
            for item in cal_items:
                if item.get("summary") == FOCUS_CALENDAR_NAME:
                    existing_id: str = str(item["id"])
                    return existing_id

            # Auto-provision dedicated secondary calendar if missing
            new_cal: Dict[str, str] = {"summary": FOCUS_CALENDAR_NAME, "timeZone": "UTC"}
            created_cal: Dict[str, Any] = self._calendar.calendars().insert(body=new_cal).execute()
            logger.info("auto_provisioned_focus_subcalendar", calendar_id=created_cal["id"])
            new_id: str = str(created_cal["id"])
            return new_id
        except Exception as e:
            err_cal: Exception = e
            logger.error("workspace_api_error_secondary_calendar", error=str(err_cal))
            raise RuntimeError(f"Failed to provision secondary focus sub-calendar: {err_cal}")

    def schedule_focus_blocks(self, plan: DailyCommitmentPlan) -> List[Dict[str, Any]]:
        """Writes focus time blocks EXCLUSIVELY to secondary sub-calendar 'EF Focus Planner'."""
        cal_id: str = self.get_or_create_secondary_focus_calendar()
        scheduled_events: List[Dict[str, Any]] = []

        if self.mock_mode:
            logger.info("workspace_service_mock_schedule_focus_blocks", blocks_count=len(plan.focus_blocks))
            for block in plan.focus_blocks:
                scheduled_events.append({
                    "event_id": f"evt_mock_{hash(block.title) % 10000}",
                    "calendar_id": cal_id,
                    "title": block.title,
                    "start_time": block.start_time,
                    "end_time": block.end_time,
                })
            return scheduled_events

        self._init_clients()
        for block in plan.focus_blocks:
            event_body: Dict[str, Any] = {
                "summary": f"[Focus] {block.title}",
                "description": f"EF Focus Planner Block for Google Task ID: {block.task_id}",
                "start": {"dateTime": block.start_time},
                "end": {"dateTime": block.end_time},
            }
            evt: Dict[str, Any] = self._calendar.events().insert(calendarId=cal_id, body=event_body).execute()
            scheduled_events.append({
                "event_id": evt["id"],
                "calendar_id": cal_id,
                "title": block.title,
                "start_time": block.start_time,
                "end_time": block.end_time,
            })
        return scheduled_events

