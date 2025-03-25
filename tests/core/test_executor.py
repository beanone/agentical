"""Tests for the ToolExecutor class."""

import pytest
from typing import Dict, Any, List

from agentical.core import ToolRegistry, ToolExecutor
from agentical.core.executor import ToolExecutionError
from agentical.types import Tool, ToolParameter, ToolCall


@pytest.fixture
def registry() -> ToolRegistry:
    """Create a test registry with tools."""
    registry = ToolRegistry()
    
    # Create test tools
    tool1 = Tool(
        name="tool1",
        description="First test tool",
        parameters={
            "param1": ToolParameter(
                type="string",
                description="Test parameter 1",
                required=True
            )
        }
    )
    
    tool2 = Tool(
        name="tool2",
        description="Second test tool",
        parameters={
            "param2": ToolParameter(
                type="number",
                description="Test parameter 2",
                required=False
            )
        }
    )
    
    # Register tools
    registry.register_tool(tool1)
    registry.register_tool(tool2)
    
    return registry


@pytest.fixture
def executor(registry: ToolRegistry) -> ToolExecutor:
    """Create a test executor with registered handlers."""
    executor = ToolExecutor(registry)
    
    # Define and register handlers
    async def handler1(params: Dict[str, Any]) -> str:
        return f"Test result 1: {params['param1']}"
        
    async def handler2(params: Dict[str, Any]) -> str:
        return f"Test result 2: {params.get('param2', 'default')}"
    
    executor.register_handler("tool1", handler1)
    executor.register_handler("tool2", handler2)
    
    return executor


@pytest.mark.asyncio
async def test_execute_tool(executor: ToolExecutor) -> None:
    """Test executing a single tool."""
    # Execute tool1
    result1 = await executor.execute_tool("tool1", {"param1": "test"})
    assert result1 == "Test result 1: test"
    
    # Execute tool2 with parameter
    result2 = await executor.execute_tool("tool2", {"param2": 42})
    assert result2 == "Test result 2: 42"
    
    # Execute tool2 without parameter (uses default)
    result3 = await executor.execute_tool("tool2", {})
    assert result3 == "Test result 2: default"


@pytest.mark.asyncio
async def test_execute_nonexistent_tool(executor: ToolExecutor) -> None:
    """Test that executing a nonexistent tool raises an error."""
    with pytest.raises(KeyError):
        await executor.execute_tool("nonexistent_tool", {})


@pytest.mark.asyncio
async def test_execute_tool_missing_required_param(executor: ToolExecutor) -> None:
    """Test that executing a tool without a required parameter raises an error."""
    with pytest.raises(ToolExecutionError):
        await executor.execute_tool("tool1", {})


@pytest.mark.asyncio
async def test_execute_tool_calls(executor: ToolExecutor) -> None:
    """Test executing multiple tool calls."""
    # Create test tool calls
    tool_calls: List[Dict[str, Any]] = [
        {
            "id": "call1",
            "name": "tool1",
            "arguments": {"param1": "test1"}
        },
        {
            "id": "call2",
            "name": "tool2",
            "arguments": {"param2": 42}
        },
        {
            "id": "call3",
            "name": "tool2",
            "arguments": {}
        }
    ]
    
    # Execute tool calls
    results = await executor.execute_tool_calls(tool_calls)
    
    # Verify results
    assert len(results) == 3
    
    assert results[0]["id"] == "call1"
    assert results[0]["output"] == "Test result 1: test1"
    
    assert results[1]["id"] == "call2"
    assert results[1]["output"] == "Test result 2: 42"
    
    assert results[2]["id"] == "call3"
    assert results[2]["output"] == "Test result 2: default"


@pytest.mark.asyncio
async def test_execute_tool_calls_with_error(executor: ToolExecutor) -> None:
    """Test that executing tool calls with an invalid tool raises an error."""
    tool_calls = [
        {
            "id": "call1",
            "name": "nonexistent_tool",
            "arguments": {}
        }
    ]
    
    with pytest.raises(KeyError):
        await executor.execute_tool_calls(tool_calls) 