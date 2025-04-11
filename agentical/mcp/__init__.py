"""MCP integration for LLM abstractions.

This package provides the integration between MCP (Machine Control Protocol)
and the LLM abstractions. It provides a high-level interface for using LLMs
with MCP tools, resources, and prompts directly.
"""

from .provider import MCPToolProvider
from .resource_registry import ResourceRegistry
from .prompt_registry import PromptRegistry
from .tool_registry import ToolRegistry

__all__ = [
    "MCPToolProvider",
    "ResourceRegistry",
    "PromptRegistry",
    "ToolRegistry",
]
