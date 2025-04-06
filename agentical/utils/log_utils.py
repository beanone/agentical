"""Utility functions for logging."""

import re
from typing import Any, Dict

def redact_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive information from log data.
    
    Args:
        data: Dictionary containing log data
        
    Returns:
        Dictionary with sensitive data redacted
    """
    SENSITIVE_KEYS = {
        'api_key', 'key', 'secret', 'password', 'token',
        'authorization', 'auth', 'credential'
    }
    
    def _redact_value(key: str, value: Any) -> Any:
        if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
            if isinstance(value, str):
                if len(value) > 8:
                    return f"{value[:4]}...{value[-4:]}"
                return "****"
            return "[REDACTED]"
        return value
    
    if not isinstance(data, dict):
        return data
        
    return {
        k: _redact_value(k, v) if isinstance(v, (str, int, float, bool)) 
        else redact_sensitive_data(v) if isinstance(v, dict)
        else v
        for k, v in data.items()
    }

def sanitize_log_message(message: str) -> str:
    """Remove sensitive patterns from log messages.
    
    Args:
        message: Log message to sanitize
        
    Returns:
        Sanitized message
    """
    # Patterns to match potential sensitive data
    patterns = [
        (r'key=[\w\-]+', 'key=****'),  # API keys
        (r'Bearer\s+[\w\-\.]+', 'Bearer ****'),  # Bearer tokens
        (r'password=[\w\-]+', 'password=****'),  # Passwords
        (r'token=[\w\-\.]+', 'token=****'),  # Tokens
        (r'secret=[\w\-]+', 'secret=****'),  # Secrets
    ]
    
    result = message
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result)
    
    return result 