"""Core abstractions for LLM integration.

This package provides the core abstractions and interfaces for integrating
with Language Learning Models (LLMs). It is designed to be implementation-agnostic,
allowing different LLM providers to implement these interfaces.
"""

from .llm_backend import LLMBackend

__all__ = [
    'LLMBackend',
] 