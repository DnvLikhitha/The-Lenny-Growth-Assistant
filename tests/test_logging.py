import pytest
from backend.logging_config import setup_logger, StructuredJsonFormatter
import logging

def test_structured_json_logging():
    logger = setup_logger()
    assert logger.name == "lenny_assistant"
    assert isinstance(logger.handlers[0].formatter, StructuredJsonFormatter)
