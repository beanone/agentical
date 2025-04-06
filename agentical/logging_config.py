"""Logging configuration for the Agentical framework."""

import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

# Module-level flag to prevent re-setup
_logging_configured = False

def setup_logging(level: Optional[int] = None, log_dir: Optional[str] = None) -> logging.Logger:
    """Configure logging for the Agentical framework.
    
    Args:
        level: The logging level to use. Defaults to INFO if not specified.
        log_dir: Optional directory for log files. If specified, will create rotating log files.
        
    Returns:
        logging.Logger: The configured agentical logger instance.
    """
    global _logging_configured
    logger = logging.getLogger("agentical")
    
    if _logging_configured:
        return logger
    
    # Reset any existing configuration
    logger.handlers.clear()
    # Allow propagation within agentical.* namespace
    logger.propagate = True
    
    # Configure logger
    level = level or logging.INFO
    
    # Configure root logger first
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Configure agentical logger
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handlers if log directory is specified
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Main log file
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "agentical.log", maxBytes=10_000_000, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Error log file
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "error.log", maxBytes=10_000_000, backupCount=5
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        logger.addHandler(error_handler)
    
    # Configure related loggers
    mcp_logger = logging.getLogger('mcp')
    mcp_logger.setLevel(level)
    mcp_logger.propagate = True
    
    # Configure third-party loggers
    if level != logging.DEBUG:
        third_party_loggers = ['asyncio', 'urllib3', 'anthropic', 'openai', 'google.generativeai']
        for name in third_party_loggers:
            third_party_logger = logging.getLogger(name)
            third_party_logger.setLevel(logging.WARNING)
    
    logger.info("Logging initialized", extra={
        "level": logging.getLevelName(level),
        "log_dir": str(log_dir) if log_dir else None
    })
    
    _logging_configured = True
    return logger