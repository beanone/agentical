"""Logging configuration for the Agentical framework."""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

def setup_logging(level: Optional[int] = None, log_dir: Optional[str] = None) -> None:
    """Configure logging for the Agentical framework.
    
    Args:
        level: Optional logging level (e.g., logging.DEBUG). If None, uses INFO.
        log_dir: Optional directory for log files. If None, only console logging is used.
    """
    level = level or logging.INFO
    
    # Define a structured log format
    formatter = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Add console handler if none exists
    if not root_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Add file handler if log directory is provided
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Main log file with rotation
        main_handler = logging.handlers.RotatingFileHandler(
            log_dir / "agentical.log",
            maxBytes=10_000_000,  # 10MB
            backupCount=5
        )
        main_handler.setFormatter(formatter)
        root_logger.addHandler(main_handler)
        
        # Error log file with rotation
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "error.log",
            maxBytes=10_000_000,  # 10MB
            backupCount=5
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)
    
    # Configure package loggers
    logging.getLogger('agentical').setLevel(level)
    logging.getLogger('mcp').setLevel(level)
    
    # Set appropriate levels for third-party loggers
    if level != logging.DEBUG:
        for logger_name in ['asyncio', 'urllib3', 'anthropic', 'openai', 'google.generativeai']:
            logging.getLogger(logger_name).setLevel(logging.WARNING)
            
    # Log startup information
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized", extra={
        "level": logging.getLevelName(level),
        "log_dir": str(log_dir) if log_dir else None
    }) 