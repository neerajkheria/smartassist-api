import re
from typing import Tuple
from app.core.telemetry import telemetry_logger

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?prior\s+rules",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"bypass\s+security"
]

class GuardrailService:
    @staticmethod
    def check_prompt_injection(text: str) -> Tuple[bool, str]:
        lowered = text.lower()
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, lowered):
                telemetry_logger.warning(f"Local Guardrail blocked injection pattern: {pattern}")
                return False, f"Blocked by SmartAssist Guardrail: Prompt injection detected ({pattern})."
        return True, "OK"

    @staticmethod
    def redact_sensitive_data(text: str) -> str:
        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]', text)
        text = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', '[REDACTED_IP]', text)
        text = re.sub(r'(sk-|Bearer\s+)[A-Za-z0-9\-_]{16,}', '[REDACTED_SECRET]', text)
        return text

    @staticmethod
    def parse_foundry_guardrail_error(error: Exception) -> Tuple[bool, str]:
        """Detects Microsoft Foundry Content Safety / Prompt Shield blocks."""
        err_str = str(error)
        if "content_filter" in err_str or "ResponsibleAIPolicyViolation" in err_str or "jailbreak" in err_str.lower():
            telemetry_logger.error(f"Microsoft Foundry Guardrail triggered: {err_str}")
            return True, "Blocked by Microsoft Foundry Guardrails (Prompt Shield / Content Safety Policy)."
        return False, err_str

guardrail_service = GuardrailService()
