"""Logging configuration for the Agentical framework."""

import logging
import sys
from typing import Optional

def setup_logging(level: Optional[int] = None) -> None:
    """Set up logging configuration.
    
    Args:
        level: Optional logging level (e.g., logging.DEBUG). If None, uses INFO.
    """
    # Set default level to INFO if not specified
    if level is None:
        level = logging.INFO
        
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
    
    # Set levels for specific loggers
    logging.getLogger('agentical').setLevel(level)
    logging.getLogger('mcp').setLevel(level)
    
    # Suppress some noisy third-party loggers when in INFO mode
    if level != logging.DEBUG:
        logging.getLogger('asyncio').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING) 