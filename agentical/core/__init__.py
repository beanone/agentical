"""Core functionality for the Agentical framework.

This module provides the fundamental building blocks:
- Type definitions for tools and messages
- Tool registry for managing available tools
- Tool executor for safe tool operations
"""

from .registry import ToolRegistry
from .executor import ToolExecutor
from .types import (
    Tool,
    ToolParameter,
    ToolResult,
    ToolHandler,
    ToolCall,
    Message
)

__all__ = [
    "Tool",
    "ToolParameter",
    "ToolResult",
    "ToolHandler",
    "ToolCall",
    "Message",
    "ToolRegistry",
    "ToolExecutor"
]
