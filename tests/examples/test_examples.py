"""Tests for example tools."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os
from typing import Dict, Any, List

from agentical.core import ToolRegistry, ToolExecutor, LLMToolIntegration
from examples.tools.examples import (
    run_weather_example,
    run_calculator_example,
    run_filesystem_example,
    run_llm_chat,
    _setup_tools,
    _setup_executor
)
from examples.tools.weather_tool import create_weather_tool
from examples.tools.calculator_tool import create_calculator_tool
from examples.tools.fs_tool import create_fs_tool


@pytest.mark.asyncio
async def test_run_weather_example() -> None:
    """Test running the weather example."""
    registry = ToolRegistry()
    weather_tool = create_weather_tool()
    registry.register_tool(weather_tool)
    executor = ToolExecutor(registry)
    
    # Mock weather handler
    async def mock_handler(params: Dict[str, Any]) -> str:
        return f"Weather for {params['location']}: Sunny, 20°C"
    
    executor.register_handler("get_weather", mock_handler)
    
    # Mock collect_weather_input to return test parameters
    with patch("examples.tools.weather_tool.collect_input", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = {"location": "London", "units": "metric"}
        await run_weather_example(executor)


@pytest.mark.asyncio
async def test_run_calculator_example() -> None:
    """Test running the calculator example."""
    registry = ToolRegistry()
    calculator_tool = create_calculator_tool()
    registry.register_tool(calculator_tool)
    executor = ToolExecutor(registry)
    
    # Mock calculator handler
    async def mock_handler(params: Dict[str, Any]) -> str:
        return "42"
    
    executor.register_handler("calculator", mock_handler)
    
    # Mock collect_calculator_input to return test parameters
    with patch("examples.tools.calculator_tool.collect_input", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = {"expression": "2 + 2"}
        await run_calculator_example(executor)


@pytest.mark.asyncio
async def test_run_filesystem_example() -> None:
    """Test running the filesystem example."""
    registry = ToolRegistry()
    fs_tool = create_fs_tool()
    registry.register_tool(fs_tool)
    executor = ToolExecutor(registry)
    
    # Mock filesystem handler
    async def mock_handler(params: Dict[str, Any]) -> str:
        return "File contents"
    
    executor.register_handler("filesystem", mock_handler)
    
    # Mock collect_filesystem_input to return test parameters
    with patch("examples.tools.fs_tool.collect_input", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = {"operation": "read", "path": "test.txt"}
        await run_filesystem_example(executor)


@pytest.mark.asyncio
async def test_run_llm_chat() -> None:
    """Test running the LLM chat."""
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    
    # Mock OpenAI API key
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        integration = LLMToolIntegration(registry, executor)
        
        # Mock OpenAI API
        with patch.object(integration, "run_conversation", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Hello! How can I help you?"
            
            # Mock user input to simulate chat interaction
            with patch("builtins.input", side_effect=["Hello", "exit"]):
                await run_llm_chat(integration)


def test_setup_tools() -> None:
    """Test setting up tools."""
    # Mock environment variables
    with patch.dict(os.environ, {"OPENWEATHERMAP_API_KEY": "test_key"}):
        registry, api_key = _setup_tools()
        
        assert isinstance(registry, ToolRegistry)
        assert api_key == "test_key"
        assert len(registry.list_tools()) == 3


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
    
    assert isinstance(executor, ToolExecutor)
    assert executor._registry == registry
    
    # Verify handlers are registered
    assert executor._handlers.get("get_weather") is not None
    assert executor._handlers.get("calculator") is not None
    assert executor._handlers.get("filesystem") is not None 