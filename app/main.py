"""FastAPI microservice runtime entrypoint for Cloud Run deployment."""

import os
import time
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Header, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.models.domain import (
    InvocationContext,
    WorkflowType,
    UserSettings,
    Chronotype,
    TriageToolContract,
    CapacityPlanningContract,
    DailyCommitmentPlan,
    EveningReflection,
    HumanApprovalToken,
)
from app.agents.router import ADKRouter
from app.agents.execution import ExecutionAgent
from app.services.auth_service import AuthService
from app.services.db_service import (
    init_db,
    get_tenant_db_session,
    async_save_memory_turn,
    async_save_evening_reflection,
)
from app.telemetry.logging import configure_logging, logger

# Initialize logging
configure_logging(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(
    title="GTD & Workload Focus Agent Service",
    description="Cloud Run containerized multi-agent system on ADK for GTD routines and Workspace APIs.",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event() -> None:
    """Application boot initialization."""
    init_db()
    logger.info("gtd_ef_agent_service_booted", environment=os.getenv("ENV", "production"))


from fastapi.responses import JSONResponse, HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def serve_web_chat_interface() -> str:
    """Serves the interactive web chat interface for testing GTD & Workload Focus Agent turns."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GTD & Workload Focus Agent</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background-color: #f4f6f9; font-family: 'Segoe UI', system-ui, sans-serif; }
    .chat-card { max-width: 900px; margin: 30px auto; border-radius: 12px; border: none; box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
    .chat-header { background: linear-gradient(135deg, #1a73e8, #0d47a1); color: white; border-top-left-radius: 12px; border-top-right-radius: 12px; padding: 20px; }
    .chat-body { height: 480px; overflow-y: auto; padding: 20px; background-color: #ffffff; }
    .msg-bubble { max-width: 80%; padding: 12px 16px; border-radius: 18px; margin-bottom: 12px; line-height: 1.5; font-size: 0.95rem; }
    .msg-user { background-color: #e3f2fd; color: #0d47a1; margin-left: auto; border-bottom-right-radius: 4px; }
    .msg-agent { background-color: #f1f3f4; color: #202124; margin-right: auto; border-bottom-left-radius: 4px; }
    .agent-badge { font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 12px; display: inline-block; margin-bottom: 6px; }
    .badge-router { background-color: #e8eaed; color: #3c4043; }
    .badge-triage { background-color: #feefc3; color: #b06000; }
    .badge-planning { background-color: #ceedd6; color: #0d652d; }
    .badge-execution { background-color: #fce8e6; color: #c5221f; }
    .chip-btn { border-radius: 20px; font-size: 0.85rem; padding: 6px 14px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="card chat-card">
      <div class="chat-header d-flex justify-content-between align-items-center">
        <div>
          <h4 class="mb-1">⚡ GTD & Workload Focus Agent</h4>
          <small class="opacity-75">Multi-Agent ADK Runtime • Gemini 2.5 Flash & Pro</small>
        </div>
        <div class="text-end">
          <span class="badge bg-success mb-1">ONLINE</span>
          <br><small class="opacity-75">User: <strong id="current-user">sjaconette</strong></small>
        </div>
      </div>
      <div class="p-3 bg-light border-bottom">
        <div class="row align-items-center">
          <div class="col-md-7">
            <label class="form-label font-weight-bold mb-1">📊 Energy & Fatigue Score Budget (1 - 10): <span id="fatigue-val" class="badge bg-primary">5</span></label>
            <input type="range" class="form-range" id="fatigue-slider" min="1" max="10" value="5" oninput="document.getElementById('fatigue-val').innerText = this.value">
          </div>
          <div class="col-md-5 text-end">
            <button class="btn btn-outline-primary chip-btn me-1" onclick="sendQuickPrompt('Please plan my focus schedule for today')">📅 Plan Schedule</button>
            <button class="btn btn-outline-warning chip-btn" onclick="sendQuickPrompt('Please help me triage my unread inbox')">📥 Triage Inbox</button>
          </div>
        </div>
      </div>
      <div class="chat-body" id="chat-window">
        <div class="msg-bubble msg-agent">
          <span class="agent-badge badge-router">ADKRouter</span>
          <div>Hello! I am your GTD and Workload Focus Assistant. How can I help you optimize your workload focus today?</div>
        </div>
      </div>
      <div class="card-footer p-3 bg-white border-top">
        <div class="input-group">
          <input type="text" id="user-input" class="form-control" placeholder="Ask to plan schedule, triage emails, or execute mutations..." onkeypress="if(event.key==='Enter') sendMessage()">
          <button class="btn btn-primary px-4" onclick="sendMessage()">Send Turn 🚀</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    let turnIndex = 0;
    const history = [];

    async function sendMessage() {
      const inputEl = document.getElementById('user-input');
      const prompt = inputEl.value.trim();
      if (!prompt) return;

      const fatigue = document.getElementById('fatigue-slider').value;
      const fullPrompt = prompt.includes('fatigue') ? prompt : `${prompt} (fatigue score ${fatigue})`;
      
      appendMessage('user', 'User', prompt);
      inputEl.value = '';
      turnIndex++;

      try {
        const res = await fetch('/api/v1/turn', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer mock_bearer_token' },
          body: JSON.stringify({ user_id: 'sjaconette', prompt: fullPrompt, turn_index: turnIndex, history: history })
        });
        const data = await res.json();
        if (data.status === 'SUCCESS') {
          renderAgentResult(data.result);
        } else {
          appendMessage('agent', 'Error', 'Failed to process turn request.');
        }
      } catch (err) {
        appendMessage('agent', 'Error', 'Network error calling /api/v1/turn: ' + err);
      }
    }

    function sendQuickPrompt(promptText) {
      document.getElementById('user-input').value = promptText;
      sendMessage();
    }

    function appendMessage(type, sender, text, badgeClass = 'badge-router') {
      const chatWin = document.getElementById('chat-window');
      const div = document.createElement('div');
      div.className = `msg-bubble msg-${type}`;
      div.innerHTML = `<span class="agent-badge ${badgeClass}">${sender}</span><div>${text}</div>`;
      chatWin.appendChild(div);
      chatWin.scrollTop = chatWin.scrollHeight;
    }

    function renderAgentResult(result) {
      const agent = result.agent || 'ADKRouter';
      let badgeClass = 'badge-router';
      if (agent === 'TriageAgent') badgeClass = 'badge-triage';
      if (agent === 'PlanningAgent') badgeClass = 'badge-planning';
      if (agent === 'ExecutionAgent') badgeClass = 'badge-execution';

      let formattedText = '';
      if (result.commitment_plan_draft) {
        const plan = result.commitment_plan_draft;
        formattedText = `<strong>Daily Focus Plan Draft Generated:</strong><br>` +
          `• Total Duration: ${plan.total_estimated_duration_minutes}m / ${plan.available_capacity_minutes}m available<br>` +
          `• P0 Frog Task: ${plan.frog_task_id}<br>` +
          `• Support Actions: ${plan.support_task_ids.join(', ')}<br>` +
          `<em>${plan.alignment_notes}</em>`;
      } else if (result.proposed_gtd_decisions) {
        formattedText = `<strong>Inbox Triage Analyzed (${result.inbox_messages.length} messages):</strong><br>` +
          result.proposed_gtd_decisions.map(d => `• Msg ${d.message_id}: <strong>${d.action_type}</strong> (${d.reasoning})`).join('<br>');
      } else if (result.response) {
        formattedText = result.response;
      } else {
        formattedText = JSON.stringify(result, null, 2);
      }

      appendMessage('agent', agent, formattedText, badgeClass);
    }
  </script>
</body>
</html>"""


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for Cloud Run container probing."""
    return {"status": "HEALTHY", "timestamp": time.time(), "version": "1.0.0"}



class TurnRequest(BaseModel):
    user_id: str = Field(..., description="Active user ID.")
    prompt: str = Field(..., description="User prompt turn content.")
    turn_index: int = Field(default=0, description="Session turn index.")
    history: List[Dict[str, str]] = Field(default_factory=list, description="Conversation history turns.")


class ApprovalRequest(BaseModel):
    user_id: str = Field(..., description="User ID confirming action.")
    action_type: str = Field(..., description="Action type ('TRIAGE_MUTATION' or 'SCHEDULE_MUTATION').")
    payload: Dict[str, Any] = Field(..., description="Confirmed payload structure.")


@app.post("/auth/login")
async def auth_login() -> Dict[str, Any]:
    """Initiates Google Account OAuth 2.0 PKCE authentication flow."""
    pkce = AuthService.generate_pkce_challenge()
    return {
        "status": "INITIATED",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "pkce": pkce,
    }


@app.post("/api/v1/turn")
async def execute_turn(
    req: TurnRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """ADK Router turn entrypoint with async background task memory persistence."""
    bearer_token = authorization.replace("Bearer ", "") if authorization else "mock_bearer_token"
    context = InvocationContext(
        user_id=req.user_id,
        bearer_token=bearer_token,
        workflow=WorkflowType.DAILY_PLANNING,
        turn_index=req.turn_index,
    )

    router = ADKRouter(bearer_token=bearer_token)
    user_settings = UserSettings(user_id=req.user_id, email=f"{req.user_id}@example.com", chronotype=Chronotype.MORNING_LARK)

    result = router.route_turn(
        user_prompt=req.prompt,
        context=context,
        history=req.history,
        user_settings=user_settings,
    )

    # Dispatch non-blocking async background task for memory persistence
    background_tasks.add_task(
        async_save_memory_turn,
        user_id=req.user_id,
        turn_index=req.turn_index,
        prompt=req.prompt,
        routed_workflow=str(result.get("routed_workflow", "UNKNOWN")),
    )

    return {"status": "SUCCESS", "turn_index": req.turn_index, "result": result}


@app.post("/api/v1/approve/gate")
async def issue_approval_gate_token(req: ApprovalRequest) -> Dict[str, Any]:
    """Human-in-the-Loop Confirmation Gate: Issues a cryptographically signed approval token."""
    token = AuthService.issue_human_approval_token(
        user_id=req.user_id,
        action_type=req.action_type,
        payload_dict=req.payload,
    )
    logger.info("human_confirmation_gate_token_issued", user_id=req.user_id, action_type=req.action_type)
    return {"status": "APPROVED", "approval_token": token.model_dump()}


@app.post("/api/v1/execute/mutation")
async def execute_approved_mutation(
    approval_token: HumanApprovalToken,
    action_type: str,
    payload: Dict[str, Any],
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Executes workspace mutation only after validating HumanApprovalToken signature."""
    bearer_token = authorization.replace("Bearer ", "") if authorization else "mock_bearer_token"
    execution_agent = ExecutionAgent(bearer_token=bearer_token)

    if action_type == "TRIAGE_MUTATION":
        contract = TriageToolContract(**payload)
        res = execution_agent.execute_triage_mutation(
            approval_token=approval_token,
            contract=contract,
            user_id=approval_token.user_id,
        )
        return {"status": "EXECUTED", "mutation_type": "TRIAGE", "result": res}

    elif action_type == "SCHEDULE_MUTATION":
        plan = DailyCommitmentPlan(**payload)
        res = execution_agent.execute_schedule_mutation(
            approval_token=approval_token,
            plan=plan,
            user_id=approval_token.user_id,
        )
        return {"status": "EXECUTED", "mutation_type": "SCHEDULE", "result": res}

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported mutation action type: {action_type}")


@app.post("/api/v1/shutdown")
async def evening_shutdown(
    reflection: EveningReflection,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """Evening shutdown routine asynchronously persisting metrics into PostgreSQL persistence."""
    # Dispatch async memory background task
    background_tasks.add_task(async_save_evening_reflection, user_id=reflection.user_id, reflection=reflection)

    logger.info(
        "evening_shutdown_logged",
        user_id=reflection.user_id,
        fatigue=reflection.fatigue_score,
        velocity=reflection.velocity_score,
    )
    return {
        "status": "SHUTDOWN_COMPLETE",
        "date": reflection.date,
        "completed_tasks": reflection.completed_tasks_count,
        "velocity_score": reflection.velocity_score,
        "message": "Session context archived. Context sliding window cleared for morning.",
    }




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
