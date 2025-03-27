"""Common test fixtures for the entire test suite."""

import pytest
from typing import Any, Dict, List, Optional, Callable
from agentical.core.types import Tool, ToolParameter


@pytest.fixture
def base_tool_parameter():
    """Base fixture for creating tool parameters.
    
    Returns:
        Callable: A factory function that creates ToolParameter instances with the given configuration.
        
    Example:
        def test_something(base_tool_parameter):
            param = base_tool_parameter(
                param_type="string",
                description="A test parameter",
                required=True,
                enum=["option1", "option2"]
            )
    """
    def _make_parameter(
        param_type: str = "string",
        description: str = "Test parameter",
        required: bool = True,
        enum: Optional[List[str]] = None,
        default: Any = None
    ) -> ToolParameter:
        return ToolParameter(
            type=param_type,
            description=description,
            required=required,
            enum=enum,
            default=default
        )
    return _make_parameter


@pytest.fixture
def base_tool():
    """Base fixture for creating tools.
    
    Returns:
        Callable: A factory function that creates Tool instances with the given configuration.
        
    Example:
        def test_something(base_tool, base_tool_parameter):
            param = base_tool_parameter(param_type="string", description="Input text")
            tool = base_tool(
                name="test_tool",
                description="A test tool",
                parameters={"input": param}
            )
    """
    def _make_tool(
        name: str,
        description: str,
        parameters: Dict[str, ToolParameter]
    ) -> Tool:
        return Tool(
            name=name,
            description=description,
            parameters=parameters
        )
    return _make_tool 