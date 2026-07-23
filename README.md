# GTD and Workload Focus Containerized Multi-Agent System

Containerized multi-agent system built on the Agent Development Kit (ADK) framework deployed to Cloud Run. The architecture orchestrates Gemini 2.5 Flash and Gemini 2.5 Pro models to execute structured Getting Things Done (GTD) routines across Google Workspace APIs (Gmail, Google Tasks, and Google Calendar).


---

## Key Features

1. **Interactive Email Triage Walkthrough**: `TriageAgent` (Gemini 2.5 Flash) turn-by-turn parsing into structured GTD decisions (`CONVERT_TO_TASK`, `MOVE_TO_REFERENCE`, `SNOOZE_DEFER`, `NO_ACTION_NEEDED`).
2. **Daily Capacity Focus Planner**: `PlanningAgent` (Gemini 2.5 Pro) multi-constraint capacity matching against fatigue score (1-10), chronotype (`MORNING_LARK`, `NIGHT_OWL`), and calendar availability.
3. **Primary Calendar Hygiene**: All focus time blocks are scheduled EXCLUSIVELY on secondary sub-calendar `EF Focus Planner`.
4. **Human-in-the-Loop Gate**: Destructive Workspace mutations require cryptographically signed `HumanApprovalToken` verification by `ExecutionAgent`.
5. **Security & Privacy**: Direct Google Account OAuth 2.0 PKCE auth, Cloud DLP API PII redaction (`[REDACTED_PHONE]`, `[REDACTED_CREDENTIAL]`), and PostgreSQL Row-Level Security (RLS) tenant isolation.
6. **Empirical Evaluation Harness**: Pytest benchmark suite enforcing 95-point compliance against the official 5 Days of AI rubric.

---

## Directory Layout

```
├── app/
│   ├── main.py                  # FastAPI Cloud Run microservice entrypoint
│   ├── models/
│   │   ├── domain.py            # Pydantic v2 schemas (extra="forbid") & contracts
│   │   └── db.py                # SQLAlchemy PostgreSQL ORM models
│   ├── agents/
│   │   ├── router.py            # ADKRouter (Gemini 2.5 Flash context compaction < 2048 tokens)
│   │   ├── triage.py            # TriageAgent (Gemini 2.5 Flash email parser)
│   │   ├── planning.py          # PlanningAgent (Gemini 2.5 Pro capacity planner)
│   │   └── execution.py         # ExecutionAgent (Gemini 2.5 Flash gate validator)
│   ├── tools/
│   │   └── gtd_tools.py         # GTDAgentTools catalog with guided error handling
│   ├── services/
│   │   ├── dlp_service.py       # Cloud DLP PII scrubber
│   │   ├── workspace_service.py # Gmail, Tasks & Calendar sub-calendar handlers
│   │   ├── auth_service.py      # OAuth 2.0 PKCE & HMAC gate signing
│   │   └── db_service.py        # RLS PostgreSQL session manager
│   └── telemetry/
│       ├── logging.py           # Structlog JSON logger emitting intent/outcome events
│       └── tracing.py           # OpenTelemetry distributed tracing spans
├── tests/
│   ├── test_schemas.py          # Strict Pydantic model tests
│   ├── test_capacity.py         # Fatigue scaling & capacity tests
│   ├── test_agents.py           # Agent routing & gate security tests
│   └── test_eval_harness.py     # 95-point assessment rubric eval harness
├── terraform/
│   ├── main.tf                  # Cloud Run, Cloud SQL, Secret Manager, KMS IaC
│   ├── variables.tf
│   └── outputs.tf
├── .github/workflows/
│   └── deploy.yml               # CI/CD pipeline with 95-point benchmark gate
├── Dockerfile                   # Multi-stage Cloud Run container build
├── pyproject.toml               # Python project configuration
└── requirements.txt             # Dependency declarations
```

---

## Running Evaluation Harness & Tests

Run the full Pytest unit and empirical evaluation harness suite:

```bash
pytest -v -s
```

Sample Evaluation Output:

```
================ 5 DAYS OF AI AGENT EVALUATION ==================
 Category 1: Tool & Interface Design  : 20 / 20
 Category 2: Context & Memory          : 20 / 20
 Category 3: Orchestration & Logic     : 20 / 20
 Category 4: Observability & Tracing   : 20 / 20
 Category 5: Infrastructure & CI/CD    : 15 / 15
 ----------------------------------------------------------------
 TOTAL COMPLIANCE EVALUATION SCORE    : 95 / 95
=================================================================
```
