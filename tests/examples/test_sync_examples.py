"""Tests for example scripts."""

import os
import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock

from examples.tools.sync_examples import (
    run_weather_example,
    run_calculator_example,
    run_filesystem_example,
    run_llm_chat,
    run_claude_chat,
    main,
    _setup_tools,
    _setup_executor
)
from examples.tools.calculator_tool import create_calculator_tool
from examples.tools.fs_tool import create_fs_tool
from examples.tools.weather_tool import create_weather_tool
from agentical.core import ToolRegistry


@pytest.mark.asyncio
async def test_run_weather_example() -> None:
    """Test running the weather example."""
    # Mock the executor
    mock_executor = AsyncMock()
    mock_executor.execute_tool = AsyncMock(return_value="Sunny, 25°C")
    
    # Mock input collection
    with patch("builtins.input", side_effect=["London", "metric"]), \
         patch("examples.tools.weather_tool.collect_input", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = {"location": "London", "units": "metric"}
        await run_weather_example(mock_executor)
        
    # Verify tool was called
    mock_executor.execute_tool.assert_called_once_with(
        "get_weather", {"location": "London", "units": "metric"}
    )


@pytest.mark.asyncio
async def test_run_calculator_example() -> None:
    """Test running the calculator example."""
    # Mock the executor
    mock_executor = AsyncMock()
    mock_executor.execute_tool = AsyncMock(return_value="4")
    
    # Mock input collection
    with patch("builtins.input", return_value="2 + 2"), \
         patch("examples.tools.calculator_tool.collect_input", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = {"expression": "2 + 2"}
        await run_calculator_example(mock_executor)
        
    # Verify tool was called
    mock_executor.execute_tool.assert_called_once_with(
        "calculator", {"expression": "2 + 2"}
    )


@pytest.mark.asyncio
async def test_run_filesystem_example():
    """Test running filesystem example."""
    # Mock the executor
    mock_executor = AsyncMock()
    mock_executor.execute_tool = AsyncMock(return_value="File contents")
    
    # Mock collect_input to return read operation
    with patch("builtins.input", side_effect=["read", "test.txt"]), \
         patch("examples.tools.sync_examples.collect_filesystem_input", new_callable=AsyncMock) as mock_input:
        mock_input.return_value = {
            "operation": "read",
            "path": "test.txt",
            "content": None
        }
        
        # Run example
        await run_filesystem_example(mock_executor)
        
        # Verify input was collected
        assert mock_input.call_count == 1
        
        # Verify tool was executed with correct parameters
        mock_executor.execute_tool.assert_called_once_with(
            "filesystem", 
            {
                "operation": "read",
                "path": "test.txt",
                "content": None
            }
        )


@pytest.mark.asyncio
async def test_run_llm_chat() -> None:
    """Test running the OpenAI chat example."""
    # Mock the integration
    mock_integration = AsyncMock()
    mock_integration.run_conversation = AsyncMock(return_value="Test response")
    
    # Mock environment and input
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}), \
         patch("builtins.input", side_effect=["Hello", "exit"]):
        await run_llm_chat(mock_integration)
        
    # Verify conversation was run
    assert mock_integration.run_conversation.call_count == 1


@pytest.mark.asyncio
async def test_run_claude_chat() -> None:
    """Test running the Claude chat example."""
    # Mock the integration
    mock_integration = AsyncMock()
    mock_integration.run_conversation = AsyncMock(return_value="Test response")
    
    # Mock environment and input
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_key"}), \
         patch("builtins.input", side_effect=["Hello", "exit"]):
        await run_claude_chat(mock_integration)
        
    # Verify conversation was run
    assert mock_integration.run_conversation.call_count == 1


@pytest.mark.asyncio
async def test_main_weather() -> None:
    """Test main function with weather mode."""
    mock_executor = AsyncMock()
    mock_executor.execute_tool = AsyncMock(return_value="Sunny, 25°C")
    
    with patch("examples.tools.sync_examples._setup_tools", return_value=(MagicMock(), "test_key")), \
         patch("examples.tools.sync_examples._setup_executor", return_value=mock_executor), \
         patch("builtins.input", side_effect=["1", "London", "metric"]), \
         patch("examples.tools.weather_tool.collect_input", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = {"location": "London", "units": "metric"}
        await main()
        
    mock_executor.execute_tool.assert_called_once()


@pytest.mark.asyncio
async def test_main_calculator() -> None:
    """Test main function with calculator mode."""
    mock_executor = AsyncMock()
    mock_executor.execute_tool = AsyncMock(return_value="4")
    
    with patch("examples.tools.sync_examples._setup_tools", return_value=(MagicMock(), None)), \
         patch("examples.tools.sync_examples._setup_executor", return_value=mock_executor), \
         patch("builtins.input", side_effect=["2", "2 + 2"]), \
         patch("examples.tools.calculator_tool.collect_input", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = {"expression": "2 + 2"}
        await main()
        
    mock_executor.execute_tool.assert_called_once()


@pytest.mark.asyncio
async def test_main_filesystem() -> None:
    """Test main function with filesystem mode."""
    mock_executor = AsyncMock()
    mock_executor.execute_tool = AsyncMock(return_value="File contents: test")
    
    with patch("examples.tools.sync_examples._setup_tools", return_value=(MagicMock(), None)), \
         patch("examples.tools.sync_examples._setup_executor", return_value=mock_executor), \
         patch("builtins.input", side_effect=["3", "read", "test.txt"]), \
         patch("examples.tools.fs_tool.collect_input", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = {"operation": "read", "path": "test.txt"}
        await main()
        
    mock_executor.execute_tool.assert_called_once()


@pytest.mark.asyncio
async def test_main_openai_chat() -> None:
    """Test main function with OpenAI chat mode."""
    mock_integration = AsyncMock()
    mock_integration.run_conversation = AsyncMock(return_value="Test response")
    
    with patch("examples.tools.sync_examples._setup_tools", return_value=(MagicMock(), None)), \
         patch("examples.tools.sync_examples._setup_executor", return_value=AsyncMock()), \
         patch("examples.tools.sync_examples.LLMToolIntegration", return_value=mock_integration), \
         patch.dict("os.environ", {"OPENAI_API_KEY": "test_key"}), \
         patch("builtins.input", side_effect=["4", "Hello", "exit"]):
        await main()
        
    mock_integration.run_conversation.assert_called_once()


@pytest.mark.asyncio
async def test_main_claude_chat() -> None:
    """Test main function with Claude chat mode."""
    mock_integration = AsyncMock()
    mock_integration.run_conversation = AsyncMock(return_value="Test response")
    
    with patch("examples.tools.sync_examples._setup_tools", return_value=(MagicMock(), None)), \
         patch("examples.tools.sync_examples._setup_executor", return_value=AsyncMock()), \
         patch("examples.tools.sync_examples.LLMToolIntegration", return_value=mock_integration), \
         patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_key"}), \
         patch("builtins.input", side_effect=["5", "Hello", "exit"]):
        await main()
        
    mock_integration.run_conversation.assert_called_once()


@pytest.mark.asyncio
async def test_main_invalid_mode() -> None:
    """Test main function with invalid mode."""
    with patch("examples.tools.sync_examples._setup_tools", return_value=(MagicMock(), None)), \
         patch("examples.tools.sync_examples._setup_executor", return_value=AsyncMock()), \
         patch("builtins.input", return_value="invalid"):
        await main()


def test_setup_tools() -> None:
    """Test setting up tools."""
    # Mock environment variables
    with patch.dict(os.environ, {"OPENWEATHERMAP_API_KEY": "test_key"}):
        registry, api_key = _setup_tools()
        
        # Verify API key was retrieved
        assert api_key == "test_key"
        
        # Verify tools were registered
        tools = registry.list_tools()
        assert len(tools) == 3
        tool_names = {tool.name for tool in tools}
        assert "get_weather" in tool_names
        assert "calculator" in tool_names
        assert "filesystem" in tool_names


def test_setup_executor() -> None:
    """Test setting up executor."""
    registry = ToolRegistry()
    api_key = "test_key"
    
    # Register tools first
    weather_tool = create_weather_tool()
    calculator_tool = create_calculator_tool()
    fs_tool = create_fs_tool()
    registry.register_tool(weather_tool)
    registry.register_tool(calculator_tool)
    registry.register_tool(fs_tool)
    
    executor = _setup_executor(registry, api_key)
    
    # Verify handlers were registered
    assert "get_weather" in executor._handlers
    assert "calculator" in executor._handlers
    assert "filesystem" in executor._handlers 