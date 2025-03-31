"""MCP integration for LLM abstractions.

This package provides the integration between MCP (Machine Control Protocol)
and the LLM abstractions. It provides a high-level interface for using LLMs 
with MCP tools directly.
"""

from .provider import MCPToolProvider

__all__ = [
    'MCPToolProvider',
] 