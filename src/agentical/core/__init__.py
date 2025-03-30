"""Core abstractions for LLM integration.

This package provides the core abstractions and interfaces for integrating
with Language Learning Models (LLMs). It is designed to be implementation-agnostic,
allowing different LLM providers to implement these interfaces.
"""

from .types import Tool, ToolParameter, ToolResult
from .llm_backend import LLMBackend

__all__ = [
    'LLMBackend',
    'Tool',
    'ToolParameter',
    'ToolResult',
] 