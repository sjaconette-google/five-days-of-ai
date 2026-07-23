"""OpenTelemetry tracing setup and span instrumentation helpers."""

import hashlib
from typing import Optional, Dict, Any
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    provider: Any = TracerProvider()
    processor: Any = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    tracer: Any = trace.get_tracer("gtd_ef_agent", "1.0.0")
except ImportError:
    trace: Optional[Any] = None
    tracer: Optional[Any] = None


class DummySpan:
    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def end(self) -> None:
        pass




def hash_user_id(user_id: str) -> str:
    """Anonymize user ID for telemetry compliance using SHA-256 hash."""
    hashed_val: str = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]
    return hashed_val


def create_agent_span(
    name: str,
    turn_id: str,
    model_name: str,
    user_id: str,
    tool_name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Any:

    """Creates an OpenTelemetry span with standardized GTD Agent context attributes."""
    if tracer is None:
        return DummySpan()

    span: Any = tracer.start_span(name)
    span.set_attribute("agent.turn_id", turn_id)
    span.set_attribute("agent.model_name", model_name)
    span.set_attribute("user.id_hash", hash_user_id(user_id))
    if tool_name:
        span.set_attribute("tool.name", tool_name)
    if attributes:
        for k, v in attributes.items():
            span.set_attribute(k, str(v))
    return span

