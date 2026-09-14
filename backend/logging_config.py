import logging
import json
import time
import sys
from typing import Optional, Dict, Any

class StructuredJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name
        }
        if hasattr(record, "request_id"):
            log_obj["request_id"] = getattr(record, "request_id")
        if hasattr(record, "session_id"):
            log_obj["session_id"] = getattr(record, "session_id")
        if hasattr(record, "provider"):
            log_obj["provider"] = getattr(record, "provider")
        if hasattr(record, "latency_ms"):
            log_obj["latency_ms"] = getattr(record, "latency_ms")
        if hasattr(record, "retrieval_score"):
            log_obj["retrieval_score"] = getattr(record, "retrieval_score")

        return json.dumps(log_obj)

def setup_logger():
    logger = logging.getLogger("lenny_assistant")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    logger.handlers = [handler]
    return logger

logger = setup_logger()
