"""Core type definitions for the LLM Layer.

These types define the core abstractions for LLM providers without depending
on specific implementation details.
"""

# Note: We've removed the tool abstractions since we're using MCP types directly.
# The core types should only contain what's needed to abstract LLM-specific details.

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


@dataclass
class ToolParameter:
    """Abstract representation of a tool parameter."""
    name: str
    description: str
    type_info: str  # Generic type information, not tied to JSON Schema
    required: bool = False
    default: Optional[Any] = None


@dataclass
class Tool:
    """Abstract representation of a tool.
    
    This is our core representation of a tool, independent of any specific
    tool format or schema system.
    """
    name: str
    description: str
    parameters: List[ToolParameter]  # List of parameters rather than schema


@dataclass
class ToolResult:
    """Abstract representation of a tool execution result."""
    content: Any  # The actual result content
    error: Optional[str] = None  # Optional error message if execution failed
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata about the execution 