"""Type definitions for the agentic framework.

This module contains the core type definitions used throughout the framework,
including Tool, ToolParameter, and related types.
"""

from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    TypedDict,
    Union,
)

from pydantic import BaseModel


class ToolParameter(BaseModel):
    """Definition of a tool parameter.
    
    Attributes:
        type: The data type of the parameter (string, number, boolean, etc.)
        description: A human-readable description of the parameter
        required: Whether the parameter is required (default: False)
        default: Default value for the parameter if not provided
        enum: Optional list of allowed values for the parameter
    """
    
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[str]] = None


class Tool(BaseModel):
    """Definition of a tool that can be executed by an agent.
    
    Attributes:
        name: The name of the tool
        description: A human-readable description of what the tool does
        parameters: Dictionary of parameter names to ToolParameter objects
    """
    
    name: str
    description: str
    parameters: Dict[str, ToolParameter]


class ToolCall(TypedDict, total=False):
    """A tool call in a message.
    
    Attributes:
        id: Unique identifier for the tool call
        type: Type of the tool call (e.g., "function")
        function: Function call details (OpenAI format)
        name: Name of the tool (Anthropic format)
        input: Tool input parameters (Anthropic format)
    """
    
    id: str
    type: str
    function: Dict[str, Any]  # name and arguments
    name: str  # Anthropic format
    input: Dict[str, Any]  # Anthropic format


class Message(TypedDict, total=False):
    """A message in a conversation.
    
    This type supports both OpenAI and Anthropic message formats.
    Required fields are 'role' and 'content'.
    Other fields are optional and depend on the provider and message type.
    
    Attributes:
        role: The role of the message sender
        content: The message content (can be None for tool calls)
        name: Name of the tool that generated the message
        tool_call_id: ID of the tool call this message responds to
        tool_calls: List of tool calls made in this message
        tool_results: List of tool results (Anthropic format)
    """
    
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str]
    name: Optional[str]
    tool_call_id: Optional[str]
    tool_calls: Optional[List[ToolCall]]
    tool_results: Optional[List[Dict[str, Any]]]  # Anthropic format


# Type aliases for tool results and handlers
ToolResult = Union[str, int, float, bool, dict, list, None]

# Support both sync and async handlers
SyncToolHandler = Callable[[Dict[str, Any]], ToolResult]
AsyncToolHandler = Callable[[Dict[str, Any]], Awaitable[ToolResult]]
ToolHandler = Union[SyncToolHandler, AsyncToolHandler] 