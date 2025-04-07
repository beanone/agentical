"""Unit tests for logging_config.py."""

import logging
from pathlib import Path

import pytest

from agentical import logging_config


@pytest.fixture(autouse=True)
def clean_logging():
    """Reset logging configuration before and after each test."""
    # Store original state
    root_logger = logging.getLogger()
    agentical_logger = logging.getLogger("agentical")
    mcp_logger = logging.getLogger("mcp")

    original_root_level = root_logger.level
    original_handlers = agentical_logger.handlers.copy()
    original_level = agentical_logger.level
    original_propagate = agentical_logger.propagate

    # Store original levels of related loggers
    third_party_loggers = [
        "asyncio",
        "urllib3",
        "anthropic",
        "openai",
        "google.generativeai",
    ]
    original_levels = {
        name: logging.getLogger(name).level for name in ["mcp"] + third_party_loggers
    }

    # Reset module-level flag
    logging_config._logging_configured = False

    # Clear handlers and reset state
    agentical_logger.handlers.clear()
    agentical_logger.setLevel(logging.NOTSET)
    agentical_logger.propagate = True

    # Reset related loggers
    for name in ["mcp"] + third_party_loggers:
        logger = logging.getLogger(name)
        logger.setLevel(logging.NOTSET)

    yield

    # Restore original state
    root_logger.setLevel(original_root_level)

    agentical_logger.handlers.clear()
    for handler in original_handlers:
        agentical_logger.addHandler(handler)
    agentical_logger.setLevel(original_level)
    agentical_logger.propagate = original_propagate

    # Restore logger levels
    for name, level in original_levels.items():
        logging.getLogger(name).setLevel(level)


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create a temporary directory for log files."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return str(log_dir)


def test_setup_logging_default_level(clean_logging):
    """Test setup_logging with default level (INFO)."""
    logger = logging_config.setup_logging()

    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert not isinstance(logger.handlers[0], logging.handlers.RotatingFileHandler)


def test_setup_logging_custom_level(clean_logging):
    """Test setup_logging with custom level."""
    logger = logging_config.setup_logging(level=logging.DEBUG)

    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)


def test_setup_logging_with_log_dir(clean_logging, temp_log_dir):
    """Test setup_logging with log directory configuration."""
    logger = logging_config.setup_logging(log_dir=temp_log_dir)

    # Should have console handler and two file handlers
    assert len(logger.handlers) == 3

    # Verify handler types
    handler_types = [type(h) for h in logger.handlers]
    assert handler_types.count(logging.StreamHandler) == 1
    assert handler_types.count(logging.handlers.RotatingFileHandler) == 2

    # Verify log files were created
    log_dir = Path(temp_log_dir)
    assert (log_dir / "agentical.log").exists()
    assert (log_dir / "error.log").exists()


def test_setup_logging_creates_log_dir(clean_logging, tmp_path):
    """Test setup_logging creates log directory if it doesn't exist."""
    log_dir = tmp_path / "nonexistent" / "logs"
    logger = logging_config.setup_logging(log_dir=str(log_dir))

    assert log_dir.exists()
    assert (log_dir / "agentical.log").exists()
    assert (log_dir / "error.log").exists()


def test_setup_logging_handler_formatting(clean_logging, temp_log_dir):
    """Test log handler formatting."""
    logger = logging_config.setup_logging(log_dir=temp_log_dir)

    for handler in logger.handlers:
        formatter = handler.formatter
        assert formatter is not None
        fmt_str = formatter._fmt
        assert "%(asctime)s.%(msecs)03d" in fmt_str
        assert "[%(levelname)s]" in fmt_str
        assert "%(name)s:" in fmt_str
        assert "%(message)s" in fmt_str


def test_setup_logging_package_levels(clean_logging):
    """Test package logger levels are set correctly."""
    logger = logging_config.setup_logging(level=logging.DEBUG)

    assert logger.level == logging.DEBUG
    assert logging.getLogger("mcp").level == logging.DEBUG


def test_setup_logging_third_party_levels(clean_logging):
    """Test third-party logger levels are set correctly."""
    logger = logging_config.setup_logging(level=logging.INFO)  # Not DEBUG

    third_party_loggers = [
        "asyncio",
        "urllib3",
        "anthropic",
        "openai",
        "google.generativeai",
    ]
    for logger_name in third_party_loggers:
        assert logging.getLogger(logger_name).level == logging.WARNING


def test_setup_logging_third_party_levels_debug(clean_logging):
    """Test third-party logger levels are not modified in DEBUG mode."""
    # First set the levels to something other than WARNING
    third_party_loggers = [
        "asyncio",
        "urllib3",
        "anthropic",
        "openai",
        "google.generativeai",
    ]
    for logger_name in third_party_loggers:
        logging.getLogger(logger_name).setLevel(logging.INFO)

    logger = logging_config.setup_logging(level=logging.DEBUG)

    # In DEBUG mode, levels should remain unchanged
    for logger_name in third_party_loggers:
        assert logging.getLogger(logger_name).level == logging.INFO


def test_setup_logging_rotating_file_config(clean_logging, temp_log_dir):
    """Test rotating file handler configuration."""
    logger = logging_config.setup_logging(log_dir=temp_log_dir)

    handlers = [
        h
        for h in logger.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]

    assert len(handlers) == 2  # Main log and error log

    for handler in handlers:
        assert handler.maxBytes == 10_000_000  # 10MB
        assert handler.backupCount == 5


def test_setup_logging_error_handler_level(clean_logging, temp_log_dir):
    """Test error log handler level configuration."""
    logger = logging_config.setup_logging(log_dir=temp_log_dir)

    error_handlers = [
        h
        for h in logger.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
        and h.baseFilename.endswith("error.log")
    ]

    assert len(error_handlers) == 1
    assert error_handlers[0].level == logging.ERROR


def test_setup_logging_multiple_calls(clean_logging):
    """Test multiple calls to setup_logging don't duplicate handlers."""
    logger1 = logging_config.setup_logging()
    initial_handlers = len(logger1.handlers)

    logger2 = logging_config.setup_logging()  # Second call

    assert logger1 is logger2  # Same logger instance
    assert len(logger2.handlers) == initial_handlers  # No new handlers
