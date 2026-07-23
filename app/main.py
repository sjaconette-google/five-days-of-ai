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
