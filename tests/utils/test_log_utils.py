"""Tests for log utilities."""

import pytest
from unittest.mock import patch, MagicMock
from agentical.utils.log_utils import sanitize_log_message

@pytest.fixture(autouse=True)
def mock_presidio_analyzer():
    """Mock Presidio analyzer to provide consistent results."""
    with patch('agentical.utils.log_utils.analyzer') as mock_analyzer:
        def analyze(text, entities, language):
            # Mock analysis results
            results = []
            text_lower = str(text).lower()
            
            # Check for sensitive patterns
            if any(key in text_lower for key in ['api_key', 'key=', 'secret', 'credential', 'password']):
                results.append(MagicMock(
                    entity_type="API_KEY",
                    start=0,
                    end=len(str(text)),
                    score=1.0
                ))
            # Specific check for bearer tokens
            elif 'bearer' in text_lower:
                results.append(MagicMock(
                    entity_type="BEARER_TOKEN",
                    start=0,
                    end=len(str(text)),
                    score=1.0
                ))
            # Check for standalone token references
            elif 'token' in text_lower and not any(safe in text_lower for safe in ['normal', 'test']):
                results.append(MagicMock(
                    entity_type="API_KEY",
                    start=0,
                    end=len(str(text)),
                    score=1.0
                ))
            return results
            
        mock_analyzer.analyze.side_effect = analyze
        yield mock_analyzer

@pytest.fixture(autouse=True)
def mock_presidio_anonymizer():
    """Mock Presidio anonymizer to provide consistent results."""
    with patch('agentical.utils.log_utils.anonymizer') as mock_anonymizer:
        def anonymize(text, analyzer_results, operators):
            return MagicMock(text="[REDACTED]")
            
        mock_anonymizer.anonymize.side_effect = anonymize
        yield mock_anonymizer

def test_sanitize_log_message_with_sensitive_data():
    """Test sanitization of log messages containing sensitive data."""
    test_cases = [
        ("API key is secret123", "[REDACTED]"),
        ("Bearer token123", "[REDACTED]"),
        ("password=secret", "[REDACTED]"),
        ("credential=xyz", "[REDACTED]"),
        ("secret_key=abc", "[REDACTED]")
    ]
    
    for input_msg, expected in test_cases:
        assert sanitize_log_message(input_msg) == expected

def test_sanitize_log_message_without_sensitive_data():
    """Test sanitization of log messages without sensitive data."""
    test_cases = [
        "Normal log message",
        "Debug info",
        "test token reference",  # Should not be redacted due to 'test' context
        "Error occurred: file not found",
        "Processing completed successfully"
    ]
    
    for message in test_cases:
        assert sanitize_log_message(message) == message

def test_sanitize_log_message_non_string():
    """Test handling of non-string input in sanitize_log_message."""
    test_cases = [
        (None, None),
        (123, 123),
        (True, True),
        (["list", "of", "items"], ["list", "of", "items"]),
        ({"key": "value"}, {"key": "value"})
    ]
    
    for input_val, expected in test_cases:
        assert sanitize_log_message(input_val) == expected

def test_sanitize_log_message_error_handling():
    """Test error handling in sanitize_log_message."""
    with patch('agentical.utils.log_utils.analyzer.analyze', side_effect=Exception("Test error")):
        message = "Test message with api_key=secret"
        # Should return original message on error
        assert sanitize_log_message(message) == message 