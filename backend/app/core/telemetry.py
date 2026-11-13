import json
import logging
import time
import uuid
from contextvars import ContextVar #Stores the request specific logs in asynchronous requests
from app.core.config import settings

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="system")

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname, #CRITICAL, INFO, ERROR, WARNING
            "logger": record.name,
            "learner_id": settings.LEARNER_ID,
            "correlation_id": correlation_id_ctx.get(),
            "message": record.getMessage()
        }
        if hasattr(record, "custom_dimensions"):
            log_payload.update(record.custom_dimensions)
        return json.dumps(log_payload)

def setup_logging() -> logging.Logger:
    logger = logging.getLogger("smartassist")
    logger.setLevel(logging.INFO) #DEBUG, INFO, WARNING, ERROR, CRITICAL
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    return logger

telemetry_logger = setup_logging()
