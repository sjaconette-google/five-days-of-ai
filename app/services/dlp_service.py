"""Cloud DLP API privacy scrubber middleware for redacting sensitive PII."""

import re
import os
from typing import Optional, Any, Dict
from app.telemetry.logging import logger

try:
    from google.cloud import dlp_v2
except ImportError:
    dlp_v2 = None


class DLPService:
    """Service wrapper for scrubbing sensitive payload tokens via Cloud DLP API."""

    project_id: str
    dlp_client: Optional[Any]

    def __init__(self, project_id: Optional[str] = None) -> None:
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "mock-gcp-project")
        if dlp_v2 and os.getenv("ENABLE_LIVE_DLP", "false").lower() == "true":
            self.dlp_client = dlp_v2.DlpServiceClient()
        else:
            self.dlp_client = None

    def redact_pii(self, text: str) -> str:
        """
        Scrubs PII (phone numbers, credentials, SSNs, credit cards) from raw text payload.
        Uses Cloud DLP API if available; falls back to regex-based sanitization.
        """
        if not text:
            return ""

        if self.dlp_client and self.project_id:
            try:
                parent: str = f"projects/{self.project_id}"
                inspect_config: Dict[str, Any] = {
                    "info_types": [
                        {"name": "PHONE_NUMBER"},
                        {"name": "CREDIT_CARD_NUMBER"},
                        {"name": "US_SOCIAL_SECURITY_NUMBER"},
                        {"name": "AUTH_TOKEN"},
                    ]
                }
                deidentify_config: Dict[str, Any] = {
                    "info_type_transformations": {
                        "transformations": [
                            {
                                "primitive_transformation": {
                                    "replace_with_info_type_config": {}
                                }
                            }
                        ]
                    }
                }
                item: Dict[str, str] = {"value": text}
                response: Any = self.dlp_client.deidentify_content(
                    request={
                        "parent": parent,
                        "deidentify_config": deidentify_config,
                        "inspect_config": inspect_config,
                        "item": item,
                    }
                )
                logger.info("dlp_redaction_success", original_len=len(text), redacted_len=len(response.item.value))
                redacted_val: str = str(response.item.value)
                return redacted_val
            except Exception as e:
                err: Exception = e
                logger.warning("dlp_api_error_fallback_to_regex", error=str(err))

        # Fallback local regex PII redaction
        sanitized: str = text
        # Redact Phone Numbers
        sanitized = re.sub(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[REDACTED_PHONE]", sanitized)
        # Redact SSN
        sanitized = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", sanitized)
        # Redact Credit Cards
        sanitized = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED_CREDENTIAL]", sanitized)
        # Redact Auth Tokens / Passwords / Bearer tokens
        sanitized = re.sub(r"(?i)(password|bearer\s+|access_token=)[^\s]+", r"\1[REDACTED_CREDENTIAL]", sanitized)

        return sanitized

