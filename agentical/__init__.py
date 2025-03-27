"""Agentical Framework: A Toolkit for Building Tool-Enabled AI Agents.

This package provides a framework for building AI agents that can interact with
various tools and APIs. It supports multiple LLM providers and offers a flexible
architecture for tool integration.

Key Components:
    - Core Types: Tool, ToolParameter, ToolResult for defining tools
    - ToolRegistry: Central registry for managing available tools
    - ToolExecutor: Executes tool operations safely
    - LLM Integration: Support for OpenAI GPT and Anthropic Claude

Example:
    ```python
    from agentical import ToolRegistry, ToolExecutor, Tool
    
    # Create a tool
    calculator_tool = Tool(
        name="calculator",
        description="Perform basic arithmetic",
        parameters=[
            ToolParameter(name="expression", type="string", required=True)
        ]
    )
    
    # Register and use the tool
    registry = ToolRegistry()
    registry.register_tool(calculator_tool)
    
    executor = ToolExecutor(registry)
    executor.register_handler("calculator", calculator_handler)
    
    # Execute the tool
    result = await executor.execute_tool("calculator", {"expression": "2 + 2"})
    ```

For more examples, see the examples/ directory in the repository.
"""

from agentical.core.types import (
    Tool,
    ToolParameter,
    ToolResult,
    ToolHandler,
    ToolCall,
    Message
)
from agentical.core import ToolRegistry, ToolExecutor
from agentical.providers.llm import LLMToolIntegration

__all__ = [
    "Tool",
    "ToolParameter",
    "ToolResult",
    "ToolHandler",
    "ToolCall",
    "Message",
    "ToolRegistry",
    "ToolExecutor",
    "LLMToolIntegration",
]

__version__ = "0.1.0"  # Add version tracking
