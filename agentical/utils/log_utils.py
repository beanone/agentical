"""Utility functions for logging."""

import logging
from typing import Any

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

# Initialize Presidio engines
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# Configure logging
logger = logging.getLogger(__name__)

# Configure redaction operators
OPERATORS = {
    "API_KEY": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
    "BEARER_TOKEN": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
    "PASSWORD": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
    "DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
}


def sanitize_log_message(message: Any) -> Any:
    """Remove sensitive patterns from log messages using Presidio.

    Args:
        message: Log message to sanitize. Can be any type, but only strings are processed.

    Returns:
        Sanitized message if input was a string, otherwise returns input unchanged
    """
    if not isinstance(message, str):
        return message

    try:
        # Analyze text for PII
        results = analyzer.analyze(
            text=message,
            entities=["API_KEY", "BEARER_TOKEN", "PASSWORD"],
            language="en",
        )

        # Anonymize if PII found
        if results:
            return anonymizer.anonymize(
                text=message, analyzer_results=results, operators=OPERATORS
            ).text
        return message
    except Exception as e:
        logger.warning(f"Error during message sanitization: {e}")
        return message  # Return original message on error
