"""Structured JSON logging with structlog emitting tool intent and outcome events."""

import sys
import logging
from typing import Dict, Any

try:
    import structlog
except ImportError:
    structlog = None



class StandardJsonLogger:
    """Fallback standard logger outputting JSON strings."""
    def __init__(self, name: str = "gtd_ef_agent") -> None:
        self._log: logging.Logger = logging.getLogger(name)
        self._log.setLevel(logging.INFO)
        if not self._log.handlers:
            handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._log.addHandler(handler)

    def info(self, event: str, **kwargs: Any) -> None:
        payload: Dict[str, Any] = {"event": event, **kwargs}
        self._log.info(str(payload))

    def warning(self, event: str, **kwargs: Any) -> None:
        payload: Dict[str, Any] = {"event": event, **kwargs}
        self._log.warning(str(payload))

    def error(self, event: str, **kwargs: Any) -> None:
        payload: Dict[str, Any] = {"event": event, **kwargs}
        self._log.error(str(payload))



def configure_logging(level: str = "INFO") -> None:
    """Configure structlog or standard logging for single-line output to stdout."""
    if structlog is not None:
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, level.upper(), logging.INFO),
        )

        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )


logger: Any = structlog.get_logger("gtd_ef_agent") if structlog is not None else StandardJsonLogger("gtd_ef_agent")



def log_tool_intent(tool_name: str, user_id: str, intent_params: Dict[str, Any]) -> None:
    """Emits tool_intent_captured JSON log event prior to tool execution."""
    logger.info(
        "tool_intent_captured",
        event_type="tool_intent_captured",
        tool_name=tool_name,
        user_id=user_id,
        intent_params=intent_params,
    )


def log_tool_outcome(tool_name: str, user_id: str, status: str, duration_ms: float, result_summary: Dict[str, Any]) -> None:
    """Emits tool_outcome_captured JSON log event upon tool execution completion."""
    logger.info(
        "tool_outcome_captured",
        event_type="tool_outcome_captured",
        tool_name=tool_name,
        user_id=user_id,
        status=status,
        duration_ms=duration_ms,
        result_summary=result_summary,
    )
